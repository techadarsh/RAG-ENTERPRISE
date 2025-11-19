#!/bin/bash
export PORT=3000
export BROWSER=none
export SKIP_PREFLIGHT_CHECK=true
export NODE_OPTIONS="--localstorage-file=/tmp/node-localstorage"
npm start
