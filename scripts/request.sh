#!/bin/bash

# Check if params were provided
if [[ -z "$1" ]]; then
  echo "Usage: '$0 <message>' or '$0 <message> <recipe>'"
  exit 1
fi

MESSAGE=$1
RECIPE=$2

# Store the JSON payload in a variable
JSON_PAYLOAD=$(cat <<EOF
{
  "model": "openai/gpt-3.5-turbo",
  "messages": [
    {"role": "system", "content": "you are a helpful assistant"},
    {"role": "user", "content": "Please echo back the following string <$MESSAGE>"}
  ]
}
EOF
)

# Store the full curl command in a variable
CURL_CMD="curl \"http://localhost:4000/chat/completions\" \\
  -H \"Content-Type: application/json\" \\
  -H \"Authorization: Bearer \$OPENAI_API_KEY\""

# Add RECIPE header only if it's set
if [ -n "$RECIPE" ]; then
  CURL_CMD="$CURL_CMD \\
  -H \"x-pangea-aig-recipe: $RECIPE\""
fi

# Append the JSON payload
CURL_CMD="$CURL_CMD \\
  -d '$JSON_PAYLOAD'"

# Print the curl command before executing it
echo "Executing command:"
echo "$CURL_CMD"
echo

# Execute the curl command
eval "$CURL_CMD"
