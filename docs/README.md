---
layout: home
permalink: index.html


repository-name: e20-3yp-tivo-desk-companion
title: Tivo – Your Friendly Interactive Assistant
---

[comment]: # "This is the standard layout for the project, but you can clean this and use your own template"

# Tivo – Your Friendly Interactive Assistant

---

## Team
-  E/20/361, Yohan Senadheera, [email](mailto:e20361@eng.pdn.ac.lk)
-  E/20/024, Buddhika Ariyarathne, [email](mailto:e20024@eng.pdn.ac.lk)
-  E/20/089, Yasiru Edirimanna, [email](mailto:e20089@eng.pdn.ac.lk)
-  E/20/366, Bhagya Senevirathna, [email](mailto:e20366@eng.pdn.ac.lk)

<!-- Image (photo/drawing of the final hardware) should be here -->

<!-- ![Tivo Concept Image](./images/tivo-concept.png) -->

#### Table of Contents
1. [Introduction](#introduction)
2. [Solution Architecture](#solution-architecture)
3. [Hardware & Software Designs](#hardware-and-software-designs)
4. [Testing](#testing)
5. [Detailed Budget](#detailed-budget)
6. [Conclusion](#conclusion)
7. [Links](#links)

## Introduction

Tivo is an innovative interactive assistant designed to enhance the user experience in interactive systems. Built with a compact, cheerful, and engaging persona, Tivo is ideal for dynamic environments where quick and friendly interactions are needed.  

This project addresses the challenge of improving efficiency and engagement in **task management** and **interactive workflows**, aiming to provide:  
- **Real-time assistance** tailored to user needs.  
- A **scalable platform** for adaptive and evolving requirements.  

## Solution Architecture

A high-level overview of Tivo’s architecture includes:  

- **Core Components**:  
  - Central Processing (Raspberry Pi 4)  
  - Peripheral Interactions (Input sensors, output feedback systems like audio or display modules)  
  - Software Modules for interaction logic.  

- **Flow Diagram**:  
  ![Architecture Diagram](./images/architecture-diagram.png)  

  Tivo processes data from user inputs, analyzes it with AI models, and provides responses via interactive media.  

## Hardware and Software Designs

### Hardware Design
- **Core Hardware**: Raspberry Pi 4 (processing), PIR sensors (motion detection), audio output modules (feedback).  
- **Additional Components**: Buttons, LEDs, and a display unit for enhanced user feedback.  

### Software Design
- **Programming Languages**: Python for control and logic.  
- **Libraries and Tools**:  
  - OpenCV for real-time input processing.  
  - Pyttsx3 for audio feedback.  
  - Pre-trained emotion recognition models (FER2013 dataset).  
- **Key Algorithms**:  
  - Real-time emotion detection using CNN models.  
  - Adaptive feedback based on contextual inputs.  

## Testing

### Hardware Testing
- **Sensors**: Tested responsiveness under various conditions (motion, light levels).  
- **Display and Audio**: Verified output consistency and quality.  

### Software Testing
- **Emotion Detection Model**: Accuracy tested on diverse datasets.  
- **System Performance**: Stress-tested for real-time responsiveness.  

## Detailed Budget

| Item               | Quantity | Unit Cost | Total     |
|---------------------|:--------:|:---------:|----------:|
| Raspberry Pi 4      | 1        | 20,000 LKR| 20,000 LKR |
| PIR Sensor          | 2        | 2,500 LKR | 5,000 LKR  |
| Speaker Module      | 1        | 1,500 LKR | 1,500 LKR  |
| Miscellaneous Items | -        | -         | 3,000 LKR  |
| **Total**           | -        | -         | **29,500 LKR** |

## Conclusion

Tivo successfully integrates interactive technologies with a focus on user-friendly design, achieving significant improvements in engagement and efficiency. Future development goals include:  
- **Integration of additional features** like natural language understanding.  
- **Deployment in commercial environments** to assess real-world performance and scalability.  

## Links

- [Project Repository](https://github.com/cepdnaclk/e20-3yp-tivo-desk-companion){:target="_blank"}
- [Project Page](https://cepdnaclk.github.io/e20-3yp-tivo-desk-companion){:target="_blank"}
- [Department of Computer Engineering](http://www.ce.pdn.ac.lk/)
- [University of Peradeniya](https://eng.pdn.ac.lk/)

[//]: # (Please refer this to learn more about Markdown syntax)
[//]: # (https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet)
