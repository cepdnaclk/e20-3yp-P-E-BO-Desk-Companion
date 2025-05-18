const express = require("express");
const AWS = require("aws-sdk");
const cors = require("cors");
require("dotenv").config();

const app = express();
app.use(cors());
app.use(express.json());

const s3 = new AWS.S3({
  region: process.env.AWS_REGION,
  accessKeyId: process.env.AWS_ACCESS_KEY_ID,
  secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
  signatureVersion: "v4",
});

app.post("/get-upload-url", async (req, res) => {
  const { username } = req.body;
  if (!username) return res.status(400).json({ error: "Username required" });

  const fileName = `user_${username
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "_")}.jpg`;

  const params = {
    Bucket: process.env.S3_BUCKET_NAME,
    Key: fileName,
    Expires: 60, // URL valid for 60 seconds
    ContentType: "image/jpeg",
    ACL: "public-read",
  };

  try {
    const uploadURL = await s3.getSignedUrlPromise("putObject", params);
    const imageUrl = `https://${process.env.S3_BUCKET_NAME}.s3.${process.env.AWS_REGION}.amazonaws.com/${fileName}`;
    res.json({ uploadURL, imageUrl });
  } catch (err) {
    console.error("Presign error:", err);
    res.status(500).json({ error: "Failed to generate URL" });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
