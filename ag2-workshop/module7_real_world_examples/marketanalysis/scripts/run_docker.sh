#!/bin/bash

docker run -d -it -e OPENAI_API_KEY=$OPENAI_API_KEY -e TAVILY_API_KEY=$TAVILY_API_KEY  -p 8008:8008 -p 8888:8888   marketanalysisacr.azurecr.io/marketanalysis:latest
