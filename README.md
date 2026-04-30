# PLPG - Personalized Learning Path Generator

A comprehensive learning management system with AI-powered personalization, quiz management, and admin dashboard.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- MongoDB 4.4+

### Backend Setup
```bash
cd backend-python
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your MongoDB URI and secrets
python app.py
```

Backend runs on `http://localhost:5000`

### Frontend Setup
```bash
cd my-react-app
npm install
cp .env.example .env
# Edit .env with your API URL
npm run dev
```

Frontend runs on `http://localhost:5173`

### Seed Data
```bash
cd backend-python
python seed_admin_roles.py    # Creates admin accounts and roles
python seed_test_users.py     # Creates test users (optional)
python seed_quiz_templates.py # Creates sample quizzes (optional)
```

## 🔐 First-Time Setup

⚠️ **IMPORTANT:** After initial deployment:
1. Log in to the admin dashboard  
2. **Change the default admin password immediately**
3. Create a new admin account for daily use
4. Disable or delete the default account

**Environment Setup:**
Before running the application, create a `.env` file with required variables:
```env
# Flask
FLASK_ENV=development
SECRET_KEY=your-secure-random-key-min-32-chars
DEBUG=False

# JWT (Required - use strong random values, min 32 characters each)
JWT_SECRET=your-jwt-secret-key-min-32-chars
JWT_REFRESH_SECRET=your-jwt-refresh-secret-min-32-chars

# MongoDB
MONGODB_URI=mongodb://localhost:27017/plpg

# Email Service
EMAIL_SERVICE=gmail
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-specific-password
```

## 📁 Project Structure

```
plpg/
├── backend-python/          # Flask API backend
│   ├── models/             # MongoDB models
│   ├── routes/             # API endpoints
│   ├── middleware/         # Auth & RBAC middleware
│   ├── services/           # Business logic
│   └── utils/              # Helper functions
├── my-react-app/           # React frontend
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   ├── pages/          # Page components
│   │   ├── services/       # API clients
│   │   └── store/          # State management
└── docs/                   # Documentation
```

## 🎯 Features

### User Features
- ✅ User registration with email verification
- ✅ JWT-based authentication
- ✅ Interest assessment quiz
- ✅ Personalized learning paths
- ✅ Quiz taking and results
- ✅ Profile management
- ✅ Password reset

### Admin Features
- ✅ Admin dashboard with analytics
- ✅ User management (CRUD, suspend, activate)
- ✅ Role management (Student ↔ Teacher)
- ✅ Password reset for users
- ✅ Real-time user list (auto-refresh)
- ✅ Search, filter, sort, paginate
- ✅ User detail modal with activity history
- ✅ CSV export
- ✅ Audit logging
- ✅ JWT + RBAC protection

### Security
- ✅ Bcrypt password hashing (12 rounds)
- ✅ JWT tokens with refresh rotation
- ✅ Rate limiting on sensitive endpoints
- ✅ Account lockout after failed attempts
- ✅ RBAC (Role-Based Access Control)
- ✅ Audit logging for compliance
- ✅ CORS protection
- ✅ Input validation & sanitization

## 🔐 Authentication Flow

### User Authentication
1. Register → Email verification → Login
2. Access token (30 min) + Refresh token (7 days)
3. Token refresh on expiry
4. Password reset via email

### Admin Authentication
1. Login with admin credentials
2. Access token (24 hours) + Refresh token (7 days)
3. RBAC permissions checked on each request
4. All actions logged to audit_logs

## 📊 API Endpoints

### User Endpoints
```
POST   /api/auth/register           - Register new user
POST   /api/auth/login              - User login
POST   /api/auth/verify-email       - Verify email
POST   /api/auth/forgot-password    - Request password reset
POST   /api/auth/reset-password     - Reset password
POST   /api/auth/refresh-token      - Refresh access token
GET    /api/auth/me                 - Get current user
```

### Admin Endpoints
```
POST   /api/admin/auth/login                    - Admin login
GET    /api/admin/users                         - List users (paginated)
GET    /api/admin/users/:id                     - Get user details
PATCH  /api/admin/users/:id/role                - Change user role
POST   /api/admin/users/:id/suspend             - Suspend user
POST   /api/admin/users/:id/activate            - Activate user
POST   /api/admin/users/:id/reset-password      - Reset user password
DELETE /api/admin/users/:id                     - Delete user
GET    /api/admin/users/export/csv              - Export users CSV
GET    /api/admin/logs                          - Audit logs
GET    /api/admin/analytics/dashboard           - Dashboard metrics
```

## 🧪 Testing

### Manual Testing
1. **User Flow:**
   - Register at `/register`
   - Check email for verification link
   - Login at `/login`
   - Take interest assessment
   - View personalized learning path

2. **Admin Flow:**
   - Login at `/admin/login`
   - Navigate to Users page
   - Search, filter, sort users
   - View user details
   - Suspend/activate/delete users
   - Export CSV
   - Check audit logs

### API Testing
```bash
# Login as admin
curl -X POST http://localhost:5000/api/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@plpg.com","password":"Admin123!"}'

# Get users (use token from login)
curl http://localhost:5000/api/admin/users?page=1&limit=10 \
  -H "Authorization: Bearer <your_token>"
```

## 🛠️ Configuration

### Environment Variables

**Backend (.env):**
```env
MONGODB_URI=mongodb://localhost:27017/plpg
JWT_SECRET=your-secret-key-here
ADMIN_JWT_SECRET=your-admin-secret-key
JWT_REFRESH_SECRET=your-refresh-secret
ADMIN_JWT_REFRESH_SECRET=your-admin-refresh-secret
FLASK_ENV=development
FRONTEND_URL=http://localhost:5173
EMAIL_TOKEN_EXPIRY_HOURS=24
RESEND_COOLDOWN_MINUTES=5
```

**Frontend (.env):**
```env
VITE_API_BASE_URL=http://localhost:5000/api
```

## 📚 Documentation

- **[Quick Start Guide](QUICK_START_GUIDE.md)** - Get started quickly
- **[Admin User Management](ADMIN_USER_MANAGEMENT_COMPLETE.md)** - Admin panel guide
- **[Admin Quick Start](ADMIN_USERS_QUICK_START.md)** - Testing checklist
- **[Auth Security](AUTH_SECURITY_FIXES.md)** - Security implementation
- **[Project Requirements](PROJECT_REQUIREMENTS.md)** - Full requirements

## 🐛 Troubleshooting

### 401 Unauthorized
- Check if logged in
- Verify token in localStorage
- Check token expiry

### CORS Errors
- Verify CORS origins in backend
- Check frontend API URL

### MongoDB Connection Failed
- Ensure MongoDB is running
- Check MONGODB_URI in .env

### Users Not Loading
- Check backend logs
- Verify admin has `users_read` permission
- Check MongoDB has users collection

## 🚀 Deployment

### Backend (Flask)
```bash
# Production server (gunicorn)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Frontend (React)
```bash
npm run build
# Serve dist/ folder with nginx or similar
```

### MongoDB
- Use MongoDB Atlas for cloud hosting
- Or self-host with proper security

## 📝 License

MIT License - See LICENSE file for details

## 👥 Contributors

- Development Team

## 🔗 Links

- [MongoDB Documentation](https://docs.mongodb.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [React Documentation](https://react.dev/)
- [Tailwind CSS](https://tailwindcss.com/)

---

**Built with ❤️ using Flask, React, MongoDB, and Tailwind CSS**
