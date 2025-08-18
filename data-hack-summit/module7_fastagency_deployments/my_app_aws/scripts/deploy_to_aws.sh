#!/bin/bash
# Script to deploy to AWS Elastic Beanstalk
# Prerequisites:
# - AWS CLI installed and configured
# - Docker installed
# - EB CLI installed

# Variables
export APPLICATION_NAME="my-app-aws"
export ENVIRONMENT_NAME="my-app-aws-env"
export AWS_REGION=${AWS_REGION:-"eu-central-1"}
export ECR_REPOSITORY="my-app-aws"
export BUCKET_NAME="my-app-aws"
export INSTANCE_PROFILE_NAME="aws-elasticbeanstalk-ec2-role"
export ROLE_NAME="aws-elasticbeanstalk-ec2-role"


# Color codes for echo
GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
RESET="\033[0m"

# Function for colored echo
colored_echo() {
    echo -e "${GREEN}$1${RESET}"
}

# Function for yellow warning echo
warning_echo() {
    echo -e "${YELLOW}$1${RESET}"
}

# Function for error echo
error_echo() {
    echo -e "${RED}$1${RESET}"
}


# Check AWS CLI configuration
echo -e "\033[0;32mChecking if AWS CLI is configured\033[0m"
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "\033[0;32mAWS CLI is not configured. Please run 'aws configure' first.\033[0m"
    exit 1
else
    echo -e "\033[0;32mAWS CLI is configured.\033[0m"
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)

if ! aws iam get-role --role-name $ROLE_NAME --region $AWS_REGION > /dev/null 2>&1; then
    colored_echo "Creating IAM role for Elastic Beanstalk EC2 instances"
    aws iam create-role \
        --region $AWS_REGION \
        --role-name $ROLE_NAME \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "ec2.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }'
fi

# Policies to attach
POLICIES=(
    "arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier"
    "arn:aws:iam::aws:policy/AWSElasticBeanstalkWorkerTier"
    "arn:aws:iam::aws:policy/AWSElasticBeanstalkMulticontainerDocker"
    "arn:aws:iam::aws:policy/AmazonECS_FullAccess"
    "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
)

# Attach policies
for POLICY_ARN in "${POLICIES[@]}"; do
    if ! aws iam list-attached-role-policies --role-name $ROLE_NAME --region $AWS_REGION | grep -q $(basename "$POLICY_ARN"); then
        colored_echo "Attaching policy: $(basename "$POLICY_ARN")"
        aws iam attach-role-policy \
            --region $AWS_REGION \
            --role-name $ROLE_NAME \
            --policy-arn "$POLICY_ARN"
    fi
done

# Create instance profile if it doesn't exist
if ! aws iam get-instance-profile --instance-profile-name $INSTANCE_PROFILE_NAME --region $AWS_REGION > /dev/null 2>&1; then
    colored_echo "Creating instance profile"
    aws iam create-instance-profile \
        --region $AWS_REGION \
        --instance-profile-name $INSTANCE_PROFILE_NAME
fi

# Remove and re-add role to instance profile
warning_echo "Ensuring role is correctly attached to instance profile"

# Remove existing role if present
CURRENT_ROLE=$(aws iam get-instance-profile --instance-profile-name $INSTANCE_PROFILE_NAME --region $AWS_REGION --query 'InstanceProfile.Roles[0].RoleName' --output text 2>/dev/null)
if [ "$CURRENT_ROLE" != "None" ] && [ -n "$CURRENT_ROLE" ]; then
    aws iam remove-role-from-instance-profile \
        --region $AWS_REGION \
        --instance-profile-name $INSTANCE_PROFILE_NAME \
        --role-name "$CURRENT_ROLE"
fi

# Add role to instance profile
aws iam add-role-to-instance-profile \
    --region $AWS_REGION \
    --instance-profile-name $INSTANCE_PROFILE_NAME \
    --role-name $ROLE_NAME

# Verify role attachment
ATTACHED_ROLE=$(aws iam get-instance-profile --instance-profile-name $INSTANCE_PROFILE_NAME --region $AWS_REGION --query 'InstanceProfile.Roles[0].RoleName' --output text)

if [ "$ATTACHED_ROLE" == "$ROLE_NAME" ]; then
    colored_echo "✅ Instance profile successfully configured"
else
    error_echo "❌ Failed to attach role to instance profile"
    exit 1
fi

# Create ECR repository if it doesn't exist
if ! aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION > /dev/null 2>&1; then
    colored_echo "Creating ECR repository"
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION
fi

# Login to AWS ECR
colored_echo "Logging into Amazon ECR"
rm ~/.docker/config.json
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws ecr describe-repositories --repository-names $ECR_REPOSITORY --query 'repositories[0].repositoryUri' --output text | sed 's/'"$ECR_REPOSITORY"'$//')

# Build Docker image
colored_echo "Building Docker image"
docker build -t $ECR_REPOSITORY:latest -f docker/Dockerfile .

# Tag and push Docker image to ECR
colored_echo "Tagging and pushing Docker image to ECR"
REPOSITORY_URI=$(aws ecr describe-repositories --repository-names $ECR_REPOSITORY --query 'repositories[0].repositoryUri' --output text --region $AWS_REGION)
docker tag $ECR_REPOSITORY:latest $REPOSITORY_URI:latest
docker push $REPOSITORY_URI:latest

colored_echo $REPOSITORY_URI

# Create Elastic Beanstalk application if it doesn't exist
colored_echo "Creating/Updating Elastic Beanstalk Application"
aws elasticbeanstalk create-application --application-name $APPLICATION_NAME --region $AWS_REGION || true

# Check if the S3 bucket exists and create it if it doesn't
if ! aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    colored_echo "Creating S3 bucket: $BUCKET_NAME"
    aws s3api create-bucket \
        --bucket "$BUCKET_NAME" \
        --region "$AWS_REGION" \
        --create-bucket-configuration LocationConstraint="$AWS_REGION"
else
    colored_echo "S3 bucket $BUCKET_NAME already exists"
fi

# Prepare Dockerrun.aws.json for Elastic Beanstalk
colored_echo "Creating Dockerrun.aws.json"
cat > Dockerrun.aws.json << EOF
{
  "AWSEBDockerrunVersion": "1",
  "Image": {
    "Name": "$REPOSITORY_URI:latest",
    "Update": "true"
  },
  "Ports": [
    {
      "ContainerPort": "8888",
      "HostPort": "80"
    },
    {
      "ContainerPort": "8888",
      "HostPort": "443"
    },
    {
      "ContainerPort": "8008",
      "HostPort": "8008"
    }
  ],
  "Volumes": []
}
EOF

# Package Dockerrun.aws.json into a ZIP file
PACKAGE_NAME="app-deployment.zip"
colored_echo "Packaging Dockerrun.aws.json into $PACKAGE_NAME"
zip -r $PACKAGE_NAME Dockerrun.aws.json

# Upload the ZIP package to S3
colored_echo "Uploading $PACKAGE_NAME to S3 bucket $BUCKET_NAME"
aws s3 cp $PACKAGE_NAME s3://$BUCKET_NAME/$PACKAGE_NAME

rm Dockerrun.aws.json $PACKAGE_NAME

# Create a new application version in Elastic Beanstalk
VERSION_LABEL="v$(date +%Y%m%d%H%M%S)"
colored_echo "Creating new application version: $VERSION_LABEL"
aws elasticbeanstalk create-application-version \
    --region "$AWS_REGION" \
    --application-name "$APPLICATION_NAME" \
    --version-label "$VERSION_LABEL" \
    --source-bundle S3Bucket="$BUCKET_NAME",S3Key="$PACKAGE_NAME"

# Create Elastic Beanstalk environment
colored_echo "Creating/Updating Elastic Beanstalk Environment"
aws elasticbeanstalk create-environment \
    --region $AWS_REGION \
    --application-name $APPLICATION_NAME \
    --environment-name $ENVIRONMENT_NAME \
    --solution-stack-name "64bit Amazon Linux 2023 v4.4.1 running Docker" \
    --option-settings '[{"Namespace":"aws:autoscaling:asg","OptionName":"MinSize","Value":"1"},{"Namespace":"aws:autoscaling:asg","OptionName":"MaxSize","Value":"2"},{"Namespace":"aws:elasticbeanstalk:environment","OptionName":"EnvironmentType","Value":"LoadBalanced"},{"Namespace":"aws:autoscaling:launchconfiguration","OptionName":"IamInstanceProfile","Value":"'$INSTANCE_PROFILE_NAME'"}]' \
    --version-label $VERSION_LABEL \
    || aws elasticbeanstalk update-environment \
        --region $AWS_REGION \
        --application-name $APPLICATION_NAME \
        --environment-name $ENVIRONMENT_NAME \
        --version-label $VERSION_LABEL

# Wait for environment to be ready and get URL
colored_echo "Waiting for environment to be ready"
aws elasticbeanstalk wait environment-updated --application-name $APPLICATION_NAME --environment-name $ENVIRONMENT_NAME --region $AWS_REGION

# Set environment variables
colored_echo "Setting environment variables"
aws elasticbeanstalk update-environment \
    --region $AWS_REGION \
    --application-name $APPLICATION_NAME \
    --environment-name $ENVIRONMENT_NAME \
    --option-settings Namespace=aws:elasticbeanstalk:application:environment,OptionName=OPENAI_API_KEY,Value=$OPENAI_API_KEY

# Wait for environment to be ready and get URL
colored_echo "Waiting for environment to be ready"
aws elasticbeanstalk wait environment-updated --application-name $APPLICATION_NAME --environment-name $ENVIRONMENT_NAME --region $AWS_REGION

# Fetch and display environment URL
ENVIRONMENT_URL=$(aws elasticbeanstalk describe-environments \
    --application-name $APPLICATION_NAME \
    --environment-names $ENVIRONMENT_NAME \
    --query "Environments[0].CNAME" \
    --output text)

colored_echo "Your AWS Elastic Beanstalk application is deployed at: http://$ENVIRONMENT_URL"
