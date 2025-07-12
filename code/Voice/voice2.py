import boto3

def text_to_baby_polly(text, output_file='baby_kevin.mp3', region='us-east-1'):
    """
    Synthesize `text` using Amazon Polly's Kevin child voice and save to MP3.
    """
    # 1. Create a Polly client
    polly = boto3.client('polly', region_name=region)  # :contentReference[oaicite:0]{index=0}

    # 2. Request speech synthesis with the Kevin voice (child voice) 
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId='Kevin',                               # child voice Kevin :contentReference[oaicite:1]{index=1}
        Engine='neural'                                 # use the high-quality NTTS engine :contentReference[oaicite:2]{index=2}
    )

    # 3. Save the binary audio stream to a file
    with open(output_file, 'wb') as f:
        f.write(response['AudioStream'].read())         # :contentReference[oaicite:3]{index=3}

    return output_file

if __name__ == '__main__':
    path = text_to_baby_polly("Hello, I'm a baby Kevin voice!")  
    print(f"Saved baby voice to {path}")
