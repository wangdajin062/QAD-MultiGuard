package com.campus.safety.model;

import com.google.gson.annotations.SerializedName;

public class ReportRequest {
    @SerializedName("report_type")
    public String reportType;   // phone|sms|link|other

    public String target;       // 手机号
    public String description;  // 描述
    public String school;       // 学校
}
