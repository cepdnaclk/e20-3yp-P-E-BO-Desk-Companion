###User_check

sudo apt install python3-boto3

#AWS
sudo apt install awscli -y
aws --version
aws configure


###Display

sudo apt install python3-pip python3-dev python3-setuptools

sudo apt install -y i2c-tools
sudo raspi-config
#Navigate to: Interfacing Options → I2C → Enable
#Reboot afterward:

sudo reboot
i2cdetect -y 1

#Image handling (drawing text/graphics)
sudo apt install python3-pillow

#SSD1306 OLED driver
pip3 install adafruit-circuitpython-ssd1306


###Assistant
sudo apt update
sudo apt install -y python3-pip python3-numpy python3-scipy python3-sounddevice

sudo apt install python3-pygame
sudo apt install python3-pyaudio

pip3 install --break-system-packages google-generativeai
pip3 install --break-system-packages edge-tts
pip3 install --break-system-packages speechrecognition

pip3 install --break-system-packages openai-whisper
pip3 install --break-system-packages sounddevice


sudo apt install ffmpeg

##new_assistant 
pip3 install scipy --break-system-packages
pip3 install aiohttp --break-system-packages
pip3 install assemblyai --break-system-packages

###record audio
pip install noisereduce --break-system-packages


AES KEY Config ( for enryption )


Step 1: Generate a Valid AES-256 Key

AES-256 requires a 32-byte key, typically encoded in base64 for easy handling (44 characters). Generate one:
bash
python3 -c "import os; import base64; print(base64.b64encode(os.urandom(32)).decode())"

Example output: <KEY>

Use this key for the steps below.
Option 1: Set AES_KEY as an Environment Variable

You can set the AES_KEY environment variable temporarily (for the current session) or permanently (persists across reboots).
Temporary (Current Session)

Set the Key:
	bash
	export AES_KEY="<KEY>"
	
Verify:
	bash
	echo $AES_KEY
	Expected: <KEY>
Test in Python:
	bash
	python3 -c "import os; print(os.getenv('AES_KEY'))"
	Expected: Same key as above.


Note: This setting is lost after closing the terminal or rebooting.
Permanent (Persists Across Sessions)

Edit ~/.bashrc:
	bash
	nano ~/.bashrc
Add the Key: At the end of the file, add:
	bash
	export AES_KEY="<KEY>"
	Save and Exit: Press Ctrl+O, Enter, then Ctrl+X.
Apply Changes:
	bash
	source ~/.bashrc
Verify:
	bash
	env | grep AES_KEY


Option 2: Store AES_KEY in .pebo_key File

Storing the key in a file (/home/pi/.pebo_key) is more secure than an environment variable, as it’s less exposed in process listings. The scripts are configured to fall back to this file if AES_KEY is not set.

Create the File:
    	bash
	echo "<KEY>" > /home/pi/.pebo_key
Set Permissions: Restrict access to the file:
	bash
	chmod 600 /home/pi/.pebo_key
Verify Contents:
	bash
	cat /home/pi/.pebo_key
Expected: <KEY>
Test Script:

Optionally, unset the environment variable to test file fallback:
    	bash
	unset AES_KEY

Expect debug output: Reading AES_KEY from /home/pi/.pebo_key

