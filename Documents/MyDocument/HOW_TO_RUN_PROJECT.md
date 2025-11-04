# How to Run DeltaCrown Project Locally

**A Simple Guide for Everyone** 👨‍💻👩‍💻

This guide will help you start and run the DeltaCrown project on your computer, even if you're not familiar with all the technical details.

---

## 📋 What You Need Before Starting

Before you can run the project, make sure you have these installed on your computer:

### Required Software:
1. **Docker Desktop** - Download from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
   - Windows: Download and install Docker Desktop for Windows
   - After installation, make sure Docker Desktop is running (you'll see a whale icon in your system tray)

2. **VS Code** (Visual Studio Code) - Download from [https://code.visualstudio.com/](https://code.visualstudio.com/)
   - This is your code editor

3. **Git** - Download from [https://git-scm.com/downloads](https://git-scm.com/downloads)
   - This helps you manage the code

---

## 🚀 Quick Start (First Time Setup)

### Step 1: Open the Project in VS Code

1. Open **VS Code**
2. Click on **File** → **Open Folder**
3. Navigate to `G:\My Projects\WORK\DeltaCrown`
4. Click **Select Folder**

### Step 2: Open Terminal in VS Code

1. In VS Code, click on **Terminal** → **New Terminal** (or press `` Ctrl + ` ``)
2. You'll see a PowerShell terminal at the bottom of VS Code

### Step 3: Configure Environment Variables (First Time Only)

Before running the project for the first time, you need to set up your environment file:

1. In VS Code, find the file named `.env.example` in the left sidebar
2. Right-click on `.env.example` and select **Copy**
3. Right-click in the same folder and select **Paste**
4. Rename the copied file from `.env.example - Copy` to `.env`

**OR** use this terminal command:
```powershell
Copy-Item .env.example .env
```

5. Open the `.env` file and change these values:
   ```
   DJANGO_SECRET_KEY=your-secret-key-change-this-to-something-random
   DB_PASSWORD=choose_a_secure_password
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   ```

   > **Note**: For `DJANGO_SECRET_KEY`, just type any random long string (at least 50 characters). Example: `my-super-secret-key-for-development-12345-abcdefghijklmnop`

### Step 4: Start the Project

Now you're ready to start everything! In the terminal, type:

```powershell
docker-compose up -d
```

**What does this do?**
- `docker-compose` - Commands Docker to set up multiple services
- `up` - Starts all the services
- `-d` - Runs everything in the background (detached mode)

**Wait 30-60 seconds** for everything to start up. Docker is starting:
- The Django application (your main project)
- PostgreSQL database
- Redis (for caching)
- Nginx (web server)
- Celery worker (for background tasks)
- Celery beat (for scheduled tasks)

### Step 5: Set Up Database (First Time Only)

After starting the project for the first time, you need to set up the database:

**Create database tables:**
```powershell
docker-compose exec django python manage.py migrate
```

**Create an admin user** (so you can log in to the admin panel):
```powershell
docker-compose exec django python manage.py createsuperuser
```

You'll be asked to enter:
- Username: (choose any username, e.g., `admin`)
- Email: (your email address)
- Password: (choose a secure password)
- Password (again): (retype the same password)

### Step 6: Access the Project

Open your web browser and go to:

- **Main Application**: [http://localhost:8000](http://localhost:8000)
- **Admin Panel**: [http://localhost:8000/admin](http://localhost:8000/admin)
- **Nginx (with static files)**: [http://localhost:8080](http://localhost:8080)

---

## 🔄 Daily Usage (After First Time Setup)

### Starting the Project

Every time you want to work on the project:

1. **Make sure Docker Desktop is running** (check for the whale icon in your system tray)

2. **Open VS Code** and open the DeltaCrown folder

3. **Open Terminal** in VS Code (`` Ctrl + ` ``)

4. **Start all services:**
   ```powershell
   docker-compose up -d
   ```

5. **Wait 30 seconds**, then open your browser to [http://localhost:8000](http://localhost:8000)

**That's it!** Your project is now running. 🎉

### Stopping the Project

When you're done working:

```powershell
docker-compose down
```

This stops all the services and frees up your computer's resources.

---

## 📝 Common Tasks

### See What's Running

To check if everything is running properly:

```powershell
docker-compose ps
```

You should see all services with "Up" status.

### View Logs (See What's Happening)

If something isn't working, you can see what's happening:

**View all logs:**
```powershell
docker-compose logs -f
```

**View just Django logs:**
```powershell
docker-compose logs -f django
```

**Stop viewing logs:** Press `Ctrl + C`

### Run Django Commands

You can run Django commands like before, but now you need to add `docker-compose exec django` before each command:

**OLD WAY (before Sprint 1):**
```powershell
python manage.py runserver 0.0.0.0:8000
```

**NEW WAY (after Sprint 1):**
```powershell
docker-compose exec django python manage.py [command]
```

**Examples:**

```powershell
# Run migrations
docker-compose exec django python manage.py migrate

# Create superuser
docker-compose exec django python manage.py createsuperuser

# Open Django shell
docker-compose exec django python manage.py shell

# Collect static files
docker-compose exec django python manage.py collectstatic

# Create new migrations
docker-compose exec django python manage.py makemigrations
```

### Run Tests

```powershell
# Run all tests
docker-compose exec django pytest

# Run tests with coverage report
docker-compose exec django pytest --cov=apps --cov-report=html

# Run specific test file
docker-compose exec django pytest tests/test_user_model.py

# Run tests with a specific marker
docker-compose exec django pytest -m unit
```

### Access Django Shell

```powershell
docker-compose exec django python manage.py shell
```

### Access Database Directly

```powershell
docker-compose exec db psql -U deltacrown -d deltacrown
```

Type `\q` to exit the database.

---

## 🔧 Troubleshooting

### Problem: "Cannot start service..."

**Solution:**
1. Stop everything: `docker-compose down`
2. Remove old containers: `docker-compose down -v`
3. Start fresh: `docker-compose up -d --build`

### Problem: "Port is already in use"

**Solution:**
Another program is using port 8000 or 5432. Either:
1. Stop the other program, OR
2. Change the port in `docker-compose.yml`

### Problem: "Docker is not running"

**Solution:**
1. Open **Docker Desktop** application
2. Wait for it to start (whale icon should appear in system tray)
3. Try the `docker-compose up -d` command again

### Problem: Changes in code don't appear

**Solution:**
1. Rebuild the Docker containers:
   ```powershell
   docker-compose up -d --build
   ```

### Problem: Database errors

**Solution:**
1. Stop everything: `docker-compose down`
2. Remove database volume: `docker-compose down -v` (⚠️ This deletes your database data!)
3. Start fresh: `docker-compose up -d`
4. Run migrations: `docker-compose exec django python manage.py migrate`
5. Create superuser: `docker-compose exec django python manage.py createsuperuser`

---

## 🆚 What Changed from Before?

### Before Sprint 1:
```powershell
# Just start Django directly
python manage.py runserver 0.0.0.0:8000
```

### After Sprint 1:
```powershell
# Start everything with Docker
docker-compose up -d

# Run Django commands through Docker
docker-compose exec django python manage.py [command]
```

### Why the Change?

**Benefits of the new way:**
- ✅ **All services in one place**: Database, cache, web server, background tasks
- ✅ **Consistent environment**: Works the same on everyone's computer
- ✅ **Easy to start**: One command starts everything
- ✅ **Isolated**: Doesn't mess with other projects on your computer
- ✅ **Production-ready**: What runs on your computer is similar to production

---

## 📚 Helpful Resources

### Important Files:

- **`.env`** - Your environment settings (passwords, secret keys)
- **`docker-compose.yml`** - Defines all services (database, cache, etc.)
- **`Dockerfile`** - Instructions for building the Django container
- **`requirements.txt`** - Python packages needed for the project

### Documentation Files:

- **`README.md`** - Main project documentation
- **`CONTRIBUTING.md`** - How to contribute to the project
- **`docs/ENVIRONMENT_CONFIGURATION.md`** - Detailed environment setup
- **`docs/SPRINT_1_COMPLETION.md`** - What was completed in Sprint 1

### Need More Help?

- Check the main README: `README.md`
- Check the environment guide: `docs/ENVIRONMENT_CONFIGURATION.md`
- Ask a team member

---

## ✅ Quick Reference Cheat Sheet

Copy these commands for quick access:

```powershell
# START PROJECT
docker-compose up -d

# STOP PROJECT
docker-compose down

# VIEW LOGS
docker-compose logs -f django

# CHECK STATUS
docker-compose ps

# RUN MIGRATIONS
docker-compose exec django python manage.py migrate

# CREATE SUPERUSER
docker-compose exec django python manage.py createsuperuser

# RUN TESTS
docker-compose exec django pytest

# RESTART EVERYTHING (if something is broken)
docker-compose down
docker-compose up -d --build

# REBUILD EVERYTHING FROM SCRATCH (⚠️ deletes database!)
docker-compose down -v
docker-compose up -d --build
docker-compose exec django python manage.py migrate
docker-compose exec django python manage.py createsuperuser
```

---

## 🎯 Summary

**To start working:**
1. Open Docker Desktop
2. Open VS Code with the DeltaCrown folder
3. Open terminal
4. Type: `docker-compose up -d`
5. Wait 30 seconds
6. Open browser: [http://localhost:8000](http://localhost:8000)

**To stop working:**
1. Type in terminal: `docker-compose down`

**To run Django commands:**
- Add `docker-compose exec django` before the command
- Example: `docker-compose exec django python manage.py migrate`

---

**That's it! You're now ready to develop the DeltaCrown project! 🚀**

If you have any questions, check the troubleshooting section or ask a team member.

---

**Last Updated**: November 4, 2025  
**Sprint**: Sprint 1 Complete  
**Author**: DeltaCrown Development Team
