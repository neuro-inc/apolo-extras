#! /bin/sh
# see tests/e2e/conftest.py line 64 comments

apolo mkdir -p storage:e2e/assets/data
apolo cp -rT tests/assets/data storage:e2e/assets/data

apolo disk get extras-e2e || exit_status=$?
if [ "${exit_status:-0}" -ne 0 ]; then
    apolo disk create --name extras-e2e --timeout-unused 1000d 100M
fi
apolo run -v storage:e2e/assets/data:/storage -v disk:extras-e2e:/disk alpine -- sh -c "mkdir -p /disk/assets && cp -rT /storage /disk/assets/data"
