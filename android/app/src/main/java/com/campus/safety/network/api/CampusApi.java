package com.campus.safety.network.api;

import com.campus.safety.model.*;

import java.util.List;
import java.util.Map;

import retrofit2.Call;
import retrofit2.http.*;

/**
 * Retrofit API interface — all backend endpoints.
 * Base URL is configured in ApiClient (debug: 10.0.2.2:8888).
 */
public interface CampusApi {

    // ── Auth ─────────────────────────────────────────────
    @POST("v1/auth/send-code")
    Call<ApiResponse<Map<String, Object>>> sendCode(@Body Map<String, Object> body);

    @POST("v1/auth/login")
    Call<ApiResponse<LoginResponse>> login(@Body Map<String, Object> body);

    @POST("v1/auth/refresh")
    Call<ApiResponse<LoginResponse>> refreshToken(@Body Map<String, Object> body);

    // ── SMS ──────────────────────────────────────────────
    @POST("v1/sms/analyze")
    Call<ApiResponse<SmsAnalyzeResult>> analyzeSms(@Body SmsAnalyzeRequest request);

    // ── Calls ────────────────────────────────────────────
    @GET("v1/calls/check")
    Call<ApiResponse<PhoneCheckResult>> checkPhone(@Query("phone") String phone);

    @GET("v1/calls/history")
    Call<ApiResponse<PageResult<CallLog>>> getCallHistory(
        @Query("page") int page,
        @Query("limit") int limit
    );

    // ── Alerts ───────────────────────────────────────────
    @GET("v1/alerts")
    Call<ApiResponse<List<FraudAlert>>> getAlerts(
        @Query("page") int page,
        @Query("limit") int limit
    );

    // ── Cases ────────────────────────────────────────────
    @GET("v1/cases")
    Call<ApiResponse<PageResult<FraudCase>>> getCases(
        @Query("category") String category,
        @Query("keyword") String keyword,
        @Query("page") int page,
        @Query("limit") int limit
    );

    @GET("v1/cases/{caseId}")
    Call<ApiResponse<FraudCase>> getCaseDetail(@Path("caseId") int caseId);

    @POST("v1/cases/{caseId}/favorite")
    Call<ApiResponse<Map<String, Object>>> toggleFavorite(@Path("caseId") int caseId);

    // ── User ─────────────────────────────────────────────
    @GET("v1/user/stats")
    Call<ApiResponse<UserStats>> getUserStats();

    @GET("v1/user/home")
    Call<ApiResponse<HomeData>> getHomeData();

    @POST("v1/user/device")
    Call<ApiResponse<Map<String, Object>>> registerDevice(@Body Map<String, Object> body);

    // ── Reports ──────────────────────────────────────────
    @POST("v1/reports")
    Call<ApiResponse<Map<String, Object>>> submitReport(@Body ReportRequest request);

    // ── Model ────────────────────────────────────────────
    @GET("v1/infer/model-status")
    Call<ApiResponse<ModelStatus>> getModelStatus();
}
