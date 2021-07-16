# Project-Uranus DataEngine Autoset Pipeline Deployment Guide

## Deployment of Resources

```bash
git clone https://github.com/aws-containers/demo-app-for-docker-compose.git
cd demo-app-for-docker-compose/application
# not sure difference between docker compose and docker-compose

cd data_engine

# and why and when to use
docker compose up 

# Navigate to the Infrastructure Directory
cd ./deployment

## following aws-cli operation requires you set your profile and region if that's not your default

# Deploy the AWS CloudFormation Template, passing in the existing AWS Resource Paramaters
aws cloudformation deploy \
--stack-name project-uranus-permissions \
--template-file ./permissions.yaml \
--capabilities CAPABILITY_IAM \
--tags \
Project=Project-uranus \
Component=Permissions

# Acquire Previous Deployment Resources ARNs

PIPELINE_ROLE_ARN=$(aws cloudformation describe-stacks --stack-name project-uranus-permissions \
--query "Stacks[0].Outputs[?OutputKey=='PipelineRoleArn'].OutputValue" --output text) && \
echo $PIPELINE_ROLE_ARN

IMAGEBUILD_ROLE_ARN=$(aws cloudformation describe-stacks --stack-name project-uranus-permissions \
--query "Stacks[0].Outputs[?OutputKey=='DataEngineImageBuildRoleArn'].OutputValue" --output text) && \
echo $IMAGEBUILD_ROLE_ARN

EXTRACTBUILD_ROLE_ARN=$(aws cloudformation describe-stacks --stack-name project-uranus-permissions \
--query "Stacks[0].Outputs[?OutputKey=='DataEngineExtractBuildRoleArn'].OutputValue" --output text) && \
echo $EXTRACTBUILD_ROLE_ARN

# Deploy Data Engine Main Resources
aws cloudformation deploy \
--stack-name project-uranus-dataengine-autoset \
--template-file ./engine_main_resources.yaml \
--capabilities CAPABILITY_IAM \
--parameter-overrides \
DataEngineImageBuildRoleArn=$IMAGEBUILD_ROLE_ARN \
DataEngineExtractBuildRoleArn=$EXTRACTBUILD_ROLE_ARN \
ProjectPipelineRoleArn=$PIPELINE_ROLE_ARN \
--tags \
Project=Project-uranus \
Component=DataEngines

```

## Pack up codes and upload to the Assets Bucket

```bash

# go back to project root
cd ../data_engine

# get the asset bucket name
ASSET_BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name project-uranus-dataengine-autoset \
--query "Stacks[0].Outputs[?OutputKey=='AssetBucketName'].OutputValue" --output text) && echo $ASSET_BUCKET_NAME

# pack the whole data_engine folder to zip and upload
zip --exclude "*.zip" -r data_engine.zip . && \
aws s3 mv "data_engine.zip" "s3://$ASSET_BUCKET_NAME/code_packs/"

```