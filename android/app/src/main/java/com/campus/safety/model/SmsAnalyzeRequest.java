package com.campus.safety.model;
import java.util.List;

import com.google.gson.annotations.SerializedName;

public class SmsAnalyzeRequest {
    public String sender;
    public List<String> keywords;

    @SerializedName("has_url")
    public boolean hasUrl;

    @SerializedName("content_length")
    public int contentLength;

    // 注意：原文不上传
}
