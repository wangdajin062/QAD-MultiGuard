package com.campus.safety.network.interceptor;

import android.content.Context;
import android.util.Log;

import com.campus.safety.BuildConfig;
import com.campus.safety.model.ApiResponse;
import com.campus.safety.model.LoginResponse;
import com.campus.safety.util.TokenManager;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import okhttp3.Authenticator;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.Route;

/**
 * OkHttp Authenticator — auto-refreshes expired access_token on 401.
 * Only triggers when a valid refresh_token is available.
 * On refresh failure, returns null so ErrorInterceptor broadcasts the 401.
 */
public class TokenRefreshAuthenticator implements Authenticator {

    private static final String TAG = "TokenRefresh";
    private static final String HEADER_REFRESHED = "X-Token-Refreshed";
    private static final MediaType JSON = MediaType.get("application/json; charset=utf-8");
    private final Context appContext;
    private final OkHttpClient refreshClient;
    private final Gson gson = new Gson();
    private final Object refreshLock = new Object();

    public TokenRefreshAuthenticator(Context context) {
        this.appContext = context.getApplicationContext();
        this.refreshClient = new OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(10, TimeUnit.SECONDS)
            .build();
    }

    @Override
    public Request authenticate(Route route, Response response) throws IOException {
        // If we already refreshed this request, don't retry again (prevents infinite loop)
        if (response.request().header(HEADER_REFRESHED) != null) {
            Log.w(TAG, "Request already refreshed — giving up");
            return null;
        }

        String refreshToken = TokenManager.getRefreshToken(appContext);
        if (refreshToken == null || refreshToken.isEmpty()) {
            Log.w(TAG, "No refresh token stored");
            return null;
        }

        // Prevent concurrent refresh calls from racing each other
        synchronized (refreshLock) {
            // Re-check after acquiring lock — another thread may have already refreshed
            String currentToken = TokenManager.getToken(appContext);
            if (currentToken != null) {
                String requestAuth = response.request().header("Authorization");
                if (requestAuth != null && requestAuth.endsWith(currentToken)) {
                    // This request already has the latest token — the new token is also invalid
                    Log.w(TAG, "Latest token also rejected — giving up");
                    return null;
                }
            }

            Log.i(TAG, "Attempting token refresh...");

            try {
                // Normalize base URL (ensure trailing slash)
                String baseUrl = BuildConfig.API_BASE_URL;
                if (!baseUrl.endsWith("/")) baseUrl += "/";

                Map<String, Object> body = new HashMap<>();
                body.put("refresh_token", refreshToken);
                String jsonBody = gson.toJson(body);

                Request refreshReq = new Request.Builder()
                    .url(baseUrl + "v1/auth/refresh")
                    .post(RequestBody.create(jsonBody, JSON))
                    .build();

                Response refreshResp = refreshClient.newCall(refreshReq).execute();

                if (!refreshResp.isSuccessful()) {
                    Log.w(TAG, "Refresh failed — HTTP " + refreshResp.code());
                    refreshResp.close();
                    return null;
                }

                String respBody = refreshResp.body() != null ? refreshResp.body().string() : "";
                refreshResp.close();

                java.lang.reflect.Type type = new TypeToken<ApiResponse<LoginResponse>>(){}.getType();
                ApiResponse<LoginResponse> apiResp = gson.fromJson(respBody, type);

                if (apiResp == null || !apiResp.isSuccess() || apiResp.data == null) {
                    Log.w(TAG, "Refresh response invalid");
                    return null;
                }

                LoginResponse lr = apiResp.data;
                TokenManager.updateTokens(appContext, lr.token, lr.refreshToken);

                Log.i(TAG, "Token refreshed successfully");

                // Retry original request with new token + marker to prevent re-refresh
                return response.request().newBuilder()
                    .header("Authorization", "Bearer " + lr.token)
                    .header(HEADER_REFRESHED, "1")
                    .build();

            } catch (Exception e) {
                Log.e(TAG, "Refresh error: " + e.getMessage(), e);
                return null;
            }
        }
    }
}
