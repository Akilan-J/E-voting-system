
# Script to view all database content by running the Python script inside the container

Write-Host "Fetching database content..." -ForegroundColor Cyan

# Copy the script into the container
docker cp scripts/view_db.py evoting_backend:/app/view_db_temp.py

# Run the script
docker exec evoting_backend python /app/view_db_temp.py

# Cleanup
docker exec evoting_backend rm /app/view_db_temp.py

Write-Host "`nDone!" -ForegroundColor Green
