#!/bin/bash

ACCOUNT_ID="259046265119"
RESOURCE_PREFIX="liveatc-flight-sonar"
REGION="us-east-1"

aws cloudformation deploy \
--stack-name "liveatc-resources-main" \
--template-file "aws_deployment/cloudformation/project_resources.yml" \
--parameter-overrides "ResourcePrefix=$RESOURCE_PREFIX" \
--tags "ProjectName=$RESOURCE_PREFIX"

read -p "Build and push the docker container? (y/n): " build_docker

if [ $build_docker == "y" ]
then
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.region.amazonaws.com
    docker build -t "$RESOURCE_PREFIX-data-pulling" "./data_pulling/"
    docker tag "$RESOURCE_PREFIX-data-pulling" \
    "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$RESOURCE_PREFIX-data-pulling-image"
    docker push "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$RESOURCE_PREFIX-data-pulling-image"
else
    echo "Skipped the docker build and push process"
fi


