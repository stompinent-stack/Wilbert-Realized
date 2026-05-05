#!/bin/bash

NAME=$1

cp -r output/project $NAME
cd $NAME

git init
git add .
git commit -m "new site"

echo "👉 Maak nu handmatig repo op GitHub:"
echo "https://github.com/new"
echo "Naam: $NAME"
echo "Druk ENTER als klaar..."

read

git branch -M main
git remote add origin https://github.com/stompinent-stack/$NAME.git
git push -u origin main

echo "✅ Gepushed → Vercel deployt automatisch"
