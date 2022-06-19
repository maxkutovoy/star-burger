#!/bin/bash

set -e

project_directory="/home/admin/star-burger"
gunicorn="star-burger-gunicorn.service"

cd $project_directory

source "./venv/bin/activate"

if [[ $(git status) == *"nothing to commit, working tree clean"* ]]
then
git pull

pip  install --upgrade pip -r requirements.txt
npm ci --dev
./node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles --public-url="./"

python manage.py collectstatic --noinput
python manage.py migrate

sudo systemctl reload nginx
sudo systemctl restart $gunicorn

echo "Deploy successful!"

. ./.env

current_commit=$(git rev-parse --verify HEAD)
report_data='{"environment": "product", "revision": '\""$current_commit"\"', "local_username": '\""$USER"\"', "status": "succeeded"}'

curl \
	-H "X-Rollbar-Access-Token: $ROLLBAR_TOKEN" \
	-H "Content-Type: application/json" \
	-X POST "https://api.rollbar.com/api/1/deploy" \
	-d "$report_data"

echo -e "\nDeploy reported to Rollbar"
else
echo $(git status)

fi
