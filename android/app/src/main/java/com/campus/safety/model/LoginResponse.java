package com.campus.safety.model;

import com.google.gson.annotations.SerializedName;

public class LoginResponse {

    @SerializedName("access_token")
    public String token;

    @SerializedName("refresh_token")
    public String refreshToken;

    @SerializedName("token_type")
    public String tokenType;

    @SerializedName("expires_in")
    public int expiresIn;

    public User user;

    public static class User {
        public long id;
        public String nickname;

        @SerializedName("protection_score")
        public int protectionScore;
    }
}
