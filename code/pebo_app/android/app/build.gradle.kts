import org.jetbrains.kotlin.gradle.tasks.KotlinCompile

val localProperties = java.util.Properties()
val localPropertiesFile = rootProject.file("local.properties")
if (localPropertiesFile.exists()) {
    localPropertiesFile.reader("UTF-8").use { reader ->
        localProperties.load(reader)
    }
}

val flutterRoot = localProperties.getProperty("flutter.sdk")
    ?: throw GradleException("Flutter SDK not found. Define location with flutter.sdk in the local.properties file.")

val flutterVersionCode = localProperties.getProperty("flutter.versionCode") ?: "1"
val flutterVersionName = localProperties.getProperty("flutter.versionName") ?: "1.0"
val kotlinVersion = rootProject.extra["kotlinVersion"] as String? ?: "1.9.0"

plugins {
    id("com.android.application")
    kotlin("android")
    id("com.google.gms.google-services") // For Firebase
}

apply(from = "$flutterRoot/packages/flutter_tools/gradle/flutter.gradle")

android {
    namespace = "com.example.pebo_app" // Use your actual package name
    compileSdk = 33
    ndkVersion = "28.0.13004108"
    
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_1_8
        targetCompatibility = JavaVersion.VERSION_1_8
    }
    
    kotlinOptions {
        jvmTarget = "1.8"
    }
    
    sourceSets {
        getByName("main") {
            java.srcDirs("src/main/kotlin")
        }
    }
    
    defaultConfig {
        applicationId = "com.example.pebo_app" // Use your actual package name
        minSdk = 21 // Required for Firebase
        targetSdk = (extra["targetSdkVersion"] as Int?) ?: 33 // Fallback if flutter.targetSdkVersion isn't available
        versionCode = flutterVersionCode.toInt()
        versionName = flutterVersionName
        multiDexEnabled = true
    }
    
    buildTypes {
        getByName("release") {
            // TODO: Add your signing config for the release build
            // Signing with the debug keys for now, so `flutter run --release` works.
            signingConfig = signingConfigs.getByName("debug")
        }
    }
}

// This is how you'd define the flutter block in Kotlin DSL
// You might need to adjust based on the actual properties available
val flutter by extra {
    object {
        val source = "../.."
    }
}

dependencies {
    implementation("org.jetbrains.kotlin:kotlin-stdlib-jdk7:$kotlinVersion")
    implementation(platform("com.google.firebase:firebase-bom:32.7.0"))
    implementation("com.google.firebase:firebase-analytics")
    implementation("com.android.support:multidex:1.0.3")
}