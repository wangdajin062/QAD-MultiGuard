package com.campus.safety.network.interceptor;

import android.content.Context;
import android.util.Log;

import com.campus.safety.util.TokenManager;

import java.io.IOException;

import okhttp3.Interceptor;
import okhttp3.Request;
import okhttp3.Response;

/**
 * Injects JWT Bearer token into every request.
 * Skips if no token is stored (pre-login state).
 */
public class AuthInterceptor implements Interceptor {

    private static final String TAG = "AuthInterceptor";
    private final Context appContext;

    public AuthInterceptor(Context context) {
        this.appContext = context.getApplicationContext();
    }

    @Override
    public Response intercept(Chain chain) throws IOException {
        Request original = chain.request();

        // Skip auth for login/send-code endpoints
        String path = original.url().encodedPath();
        if (path.contains("/auth/")) {
            return chain.proceed(original);
        }

        String token = TokenManager.getToken(appContext);
        if (token == null || token.isEmpty()) {
            return chain.proceed(original);
        }

        Request authenticated = original.newBuilder()
            .header("Authorization", "Bearer " + token)
            .build();

        return chain.proceed(authenticated);
    }
}
