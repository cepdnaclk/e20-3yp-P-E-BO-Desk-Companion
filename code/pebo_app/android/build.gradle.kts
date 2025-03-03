buildscript {
    repositories {
        google()
        mavenCentral()
    }
    dependencies {
        classpath("com.android.tools.build:gradle:7.3.0")
        classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:1.9.0")
        // Add this line to include Google Services
        classpath("com.google.gms:google-services:4.4.0")
    }
}

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

// Set the build directory correctly using File
rootProject.buildDir = File("../build")

subprojects {
    project.buildDir = File("${rootProject.buildDir}/${project.name}")
}

// For pre-Gradle 7.0
subprojects {
    project.evaluationDependsOn(":app")
}

// For Gradle 7.0+
tasks.register<Delete>("clean") {
    delete(rootProject.buildDir)
}