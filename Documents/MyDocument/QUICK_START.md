# 🚀 Quick Start Guide - DeltaCrown Project

**For Complete Beginners** - 5 Minutes to Get Started!

---

## 📥 What You Need to Install

1. **Docker Desktop** → [Download Here](https://www.docker.com/products/docker-desktop)
2. **VS Code** → [Download Here](https://code.visualstudio.com/)

---

## ⚡ First Time Setup (Do This Once)

### Step 1: Open Project
- Open **VS Code**
- Click **File** → **Open Folder**
- Select: `G:\My Projects\WORK\DeltaCrown`

### Step 2: Open Terminal
- In VS Code, press: **Ctrl + `** (that's the backtick key, usually next to number 1)

### Step 3: Copy Environment File
Type this in the terminal:
```powershell
Copy-Item .env.example .env
```

### Step 4: Start Everything
Type this in the terminal:
```powershell
docker-compose up -d
```
⏱️ **Wait 30-60 seconds...**

### Step 5: Set Up Database
Type these commands **one by one**:
```powershell
docker-compose exec django python manage.py migrate

docker-compose exec django python manage.py createsuperuser
```
(Enter a username, email, and password when asked)

### Step 6: Open in Browser
Click this link: [http://localhost:8000](http://localhost:8000)

✅ **Done!** Your project is running!

---

## 🔄 Daily Use (After First Setup)

### To Start Project:
1. Make sure **Docker Desktop** is running (check system tray)
2. Open **VS Code** with DeltaCrown folder
3. Open terminal (**Ctrl + `**)
4. Type:
   ```powershell
   docker-compose up -d
   ```
5. Wait 30 seconds, then open: [http://localhost:8000](http://localhost:8000)

### To Stop Project:
```powershell
docker-compose down
```

---

## 💡 Common Commands

### Run Django Commands:
Always add `docker-compose exec django` before any Python command:

```powershell
# Old way (before Sprint 1):
python manage.py runserver

# New way (after Sprint 1):
docker-compose exec django python manage.py [command]
```

### Useful Commands:

| Task | Command |
|------|---------|
| **Run migrations** | `docker-compose exec django python manage.py migrate` |
| **Create admin user** | `docker-compose exec django python manage.py createsuperuser` |
| **See logs** | `docker-compose logs -f django` |
| **Check status** | `docker-compose ps` |
| **Run tests** | `docker-compose exec django pytest` |
| **Stop project** | `docker-compose down` |

---

## 🆘 Something Broken?

### Quick Fix (Works 90% of the time):
```powershell
docker-compose down
docker-compose up -d --build
```

### Nuclear Option (Deletes everything and starts fresh):
```powershell
docker-compose down -v
docker-compose up -d --build
docker-compose exec django python manage.py migrate
docker-compose exec django python manage.py createsuperuser
```
⚠️ **Warning**: This deletes your database!

---

## 🎯 Summary

**Start:** `docker-compose up -d` → Wait 30s → [http://localhost:8000](http://localhost:8000)

**Stop:** `docker-compose down`

**Run Django Commands:** Add `docker-compose exec django` before any command

**Need Help?** Check the full guide: `Documents/MyDocument/HOW_TO_RUN_PROJECT.md`

---

**That's all you need to know! Happy coding! 🎉**
