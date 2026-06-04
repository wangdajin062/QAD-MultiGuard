package com.campus.safety.network.interceptor;

import android.content.Context;
import android.content.Intent;
import android.util.Log;

import androidx.localbroadcastmanager.content.LocalBroadcastManager;

import java.io.IOException;

import okhttp3.Interceptor;
import okhttp3.Response;

/**
 * HTTP error interceptor — broadcasts local intents on auth/rate/server errors
 * so that UI components (MainActivity, etc.) can react without coupling.
 */
public class ErrorInterceptor implements Interceptor {

    public static final String ACTION_UNAUTHORIZED  = "com.campus.safety.ACTION_UNAUTHORIZED";
    public static final String ACTION_RATE_LIMITED   = "com.campus.safety.ACTION_RATE_LIMITED";
    public static final String ACTION_SERVER_ERROR   = "com.campus.safety.ACTION_SERVER_ERROR";

    private static final String TAG = "ErrorInterceptor";
    private final Context appContext;

    public ErrorInterceptor(Context context) {
        this.appContext = context.getApplicationContext();
    }

    @Override
    public Response intercept(Chain chain) throws IOException {
        Response response = chain.proceed(chain.request());

        if (!response.isSuccessful()) {
            int code = response.code();
            String action = null;

            if (code == 401) {
                action = ACTION_UNAUTHORIZED;
            } else if (code == 429) {
                action = ACTION_RATE_LIMITED;
            } else if (code >= 500) {
                action = ACTION_SERVER_ERROR;
            }

            if (action != null) {
                Log.w(TAG, "HTTP " + code + " → broadcasting " + action);
                Intent intent = new Intent(action);
                LocalBroadcastManager.getInstance(appContext).sendBroadcast(intent);
            }
        }

        return response;
    }
}
