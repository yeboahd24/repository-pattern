#!/bin/bash

# Create a new user
curl -X POST http://localhost:8080/users/create \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john.doe@example.com"}'

echo -e "\n\nNow fetching all users:"
# Get all users to verify the creation
curl -X GET http://localhost:8080/users
