"""
Quick S3 connection test for EduGenAI.
Run: python test_s3_connection.py
"""
import sys
import os

# Load .env
from dotenv import load_dotenv
load_dotenv()

AWS_ACCESS_KEY_ID     = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION            = os.getenv("AWS_REGION", "ap-south-1")
AWS_S3_BUCKET_NAME    = os.getenv("AWS_S3_BUCKET_NAME", "")

print("=" * 55)
print("  EduGenAI — AWS S3 Connection Test")
print("=" * 55)

# ── Step 1: Check credentials exist ──────────────────────────
print("\n[1] Checking credentials in .env...")
missing = []
if not AWS_ACCESS_KEY_ID:     missing.append("AWS_ACCESS_KEY_ID")
if not AWS_SECRET_ACCESS_KEY: missing.append("AWS_SECRET_ACCESS_KEY")
if not AWS_S3_BUCKET_NAME:    missing.append("AWS_S3_BUCKET_NAME")

if missing:
    print(f"  ❌ Missing keys: {', '.join(missing)}")
    print("\n  👉 Open backend/.env and fill in:")
    for k in missing:
        print(f"       {k}=<your-value>")
    sys.exit(1)

print(f"  ✅ AWS_ACCESS_KEY_ID  : {AWS_ACCESS_KEY_ID[:6]}...{AWS_ACCESS_KEY_ID[-4:]}")
print(f"  ✅ AWS_SECRET_ACCESS_KEY : ***hidden***")
print(f"  ✅ AWS_REGION         : {AWS_REGION}")
print(f"  ✅ AWS_S3_BUCKET_NAME : {AWS_S3_BUCKET_NAME}")

# ── Step 2: Import boto3 ─────────────────────────────────────
print("\n[2] Importing boto3...")
try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    print("  ✅ boto3 is installed")
except ImportError:
    print("  ❌ boto3 not installed. Run: pip install boto3")
    sys.exit(1)

# ── Step 3: Connect to S3 ────────────────────────────────────
print("\n[3] Connecting to S3...")
try:
    s3 = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION,
    )
    print("  ✅ S3 client created")
except Exception as e:
    print(f"  ❌ Failed to create S3 client: {e}")
    sys.exit(1)

# ── Step 4: Check bucket exists & accessible ─────────────────
print(f"\n[4] Checking bucket '{AWS_S3_BUCKET_NAME}'...")
try:
    s3.head_bucket(Bucket=AWS_S3_BUCKET_NAME)
    print(f"  ✅ Bucket exists and is accessible!")
except ClientError as e:
    code = e.response["Error"]["Code"]
    if code == "404":
        print(f"  ❌ Bucket '{AWS_S3_BUCKET_NAME}' does NOT exist.")
        print("     Create it in AWS Console → S3 → Create bucket")
    elif code == "403":
        print(f"  ❌ Access denied to bucket '{AWS_S3_BUCKET_NAME}'.")
        print("     Check your IAM user has: s3:GetObject, s3:PutObject, s3:ListBucket")
    elif code == "InvalidClientTokenId":
        print("  ❌ Invalid AWS_ACCESS_KEY_ID — check your key.")
    elif code == "SignatureDoesNotMatch":
        print("  ❌ Invalid AWS_SECRET_ACCESS_KEY — check your secret.")
    else:
        print(f"  ❌ AWS error ({code}): {e}")
    sys.exit(1)
except NoCredentialsError:
    print("  ❌ No credentials found. Check .env is loaded correctly.")
    sys.exit(1)

# ── Step 5: Test upload tiny file ────────────────────────────
print("\n[5] Testing upload with a small test file...")
try:
    test_key = "test/edugenai_connection_test.txt"
    s3.put_object(
        Bucket=AWS_S3_BUCKET_NAME,
        Key=test_key,
        Body=b"EduGenAI S3 connection test OK",
        ContentType="text/plain",
    )
    url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{test_key}"
    print(f"  ✅ Test file uploaded!")
    print(f"     URL: {url}")

    # Clean up
    s3.delete_object(Bucket=AWS_S3_BUCKET_NAME, Key=test_key)
    print(f"  ✅ Test file cleaned up.")
except ClientError as e:
    print(f"  ❌ Upload failed: {e}")
    print("     Make sure IAM user has s3:PutObject permission on this bucket.")
    sys.exit(1)

# ── Done ─────────────────────────────────────────────────────
print("\n" + "=" * 55)
print("  S3 is fully connected and working!")
print("     Videos will automatically upload to S3 after generation.")
print("=" * 55)
