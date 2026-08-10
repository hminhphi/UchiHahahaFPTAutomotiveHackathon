plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

android {
    namespace = "io.fleetiq.hmi"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.fleetiq.hmi"
        minSdk = 29
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"

        val bridgeUrl = providers.gradleProperty("FLEETIQ_BRIDGE_URL")
            .orElse("http://10.0.2.2:8090")
        buildConfigField("String", "CARSKY_BRIDGE_URL", "\"${bridgeUrl.get()}\"")

        val vehicleId = providers.gradleProperty("FLEETIQ_VEHICLE_ID")
            .orElse("vehicle-1")
        buildConfigField("String", "VEHICLE_ID", "\"${vehicleId.get()}\"")

        val apiUrl = providers.gradleProperty("FLEETIQ_API_URL")
            .orElse("http://10.0.2.2:8000")
        buildConfigField("String", "FLEETIQ_API_URL", "\"${apiUrl.get()}\"")
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    testOptions {
        unitTests.isIncludeAndroidResources = false
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")

    implementation(composeBom)
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.7")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.9.0")
}
