package com.campus.safety.model;

import com.google.gson.annotations.SerializedName;

public class CallLog {
    public long id;

    @SerializedName("phone_number")
    public String phoneNumber;

    @SerializedName("risk_level")
    public String riskLevel;

    @SerializedName("detection_type")
    public String detectionType;

    @SerializedName("detected_at")
    public String detectedAt;
}
