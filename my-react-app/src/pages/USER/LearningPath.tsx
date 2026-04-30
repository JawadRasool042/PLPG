import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';

const DOMAIN_DATA: Record<string, {
  icon: string;
  color: string;
  description: string;
  roadmap: { phase: string; topics: string[]; duration: string }[];
  courses: { name: string; platform: string; url: string; free: boolean }[];
  projects: string[];
  careers: string[];
}> = {
  'AI & Machine Learning': {
    icon: '🤖', color: 'from-purple-500 to-indigo-600',
    description: 'Build intelligent systems that learn from data. One of the most in-demand fields in tech.',
    roadmap: [
      { phase: 'Foundation', topics: ['Python Basics', 'NumPy & Pandas', 'Statistics & Math'], duration: '4-6 weeks' },
      { phase: 'Core ML', topics: ['Supervised Learning', 'Unsupervised Learning', 'Model Evaluation'], duration: '6-8 weeks' },
      { phase: 'Deep Learning', topics: ['Neural Networks', 'CNNs', 'RNNs', 'Transformers'], duration: '8-10 weeks' },
      { phase: 'Specialization', topics: ['NLP', 'Computer Vision', 'Reinforcement Learning'], duration: '8-12 weeks' },
      { phase: 'Projects', topics: ['Kaggle Competitions', 'Research Papers', 'Deploy Models'], duration: 'Ongoing' },
    ],
    courses: [
      { name: 'Machine Learning by Andrew Ng', platform: 'Coursera', url: 'https://coursera.org/learn/machine-learning', free: false },
      { name: 'Fast.ai Practical Deep Learning', platform: 'fast.ai', url: 'https://fast.ai', free: true },
      { name: 'CS229 Stanford ML', platform: 'YouTube', url: 'https://youtube.com/playlist?list=PLoROMvodv4rMiGQp3WXShtMGgzqpfVfbU', free: true },
      { name: 'Kaggle ML Courses', platform: 'Kaggle', url: 'https://kaggle.com/learn', free: true },
    ],
    projects: ['Image Classifier', 'Sentiment Analysis Tool', 'Recommendation System', 'Chatbot with NLP', 'Stock Price Predictor'],
    careers: ['ML Engineer', 'Data Scientist', 'AI Researcher', 'NLP Engineer', 'Computer Vision Engineer'],
  },
  'Web Development': {
    icon: '🌐', color: 'from-blue-500 to-cyan-600',
    description: 'Build websites and web applications used by millions. Full-stack development opens endless opportunities.',
    roadmap: [
      { phase: 'Frontend Basics', topics: ['HTML5', 'CSS3', 'JavaScript ES6+'], duration: '4-6 weeks' },
      { phase: 'Frontend Framework', topics: ['React.js', 'State Management', 'REST APIs'], duration: '6-8 weeks' },
      { phase: 'Backend', topics: ['Node.js', 'Express', 'Databases (SQL/NoSQL)'], duration: '6-8 weeks' },
      { phase: 'Full Stack', topics: ['Authentication', 'Deployment', 'Docker'], duration: '4-6 weeks' },
      { phase: 'Advanced', topics: ['TypeScript', 'Testing', 'Performance', 'Security'], duration: 'Ongoing' },
    ],
    courses: [
      { name: 'The Odin Project', platform: 'theodinproject.com', url: 'https://theodinproject.com', free: true },
      { name: 'Full Stack Open', platform: 'University of Helsinki', url: 'https://fullstackopen.com', free: true },
      { name: 'freeCodeCamp', platform: 'freeCodeCamp', url: 'https://freecodecamp.org', free: true },
      { name: 'Web Dev Bootcamp', platform: 'Udemy', url: 'https://udemy.com', free: false },
    ],
    projects: ['Portfolio Website', 'Blog Platform', 'E-commerce Store', 'Social Media App', 'Real-time Chat App'],
    careers: ['Frontend Developer', 'Backend Developer', 'Full Stack Developer', 'UI/UX Developer', 'DevOps Engineer'],
  },
  'Cybersecurity': {
    icon: '🔐', color: 'from-red-500 to-rose-600',
    description: 'Protect systems and networks from digital attacks. Cybersecurity professionals are in massive demand.',
    roadmap: [
      { phase: 'Fundamentals', topics: ['Networking Basics', 'Linux', 'Windows Security'], duration: '4-6 weeks' },
      { phase: 'Security Concepts', topics: ['Cryptography', 'Authentication', 'Firewalls'], duration: '4-6 weeks' },
      { phase: 'Ethical Hacking', topics: ['Penetration Testing', 'OWASP Top 10', 'Kali Linux'], duration: '8-10 weeks' },
      { phase: 'Specialization', topics: ['Web App Security', 'Network Security', 'Forensics'], duration: '8-12 weeks' },
      { phase: 'Certifications', topics: ['CompTIA Security+', 'CEH', 'OSCP'], duration: 'Ongoing' },
    ],
    courses: [
      { name: 'TryHackMe', platform: 'TryHackMe', url: 'https://tryhackme.com', free: true },
      { name: 'HackTheBox', platform: 'HackTheBox', url: 'https://hackthebox.com', free: true },
      { name: 'Cybersecurity Specialization', platform: 'Coursera', url: 'https://coursera.org', free: false },
      { name: 'CS50 Cybersecurity', platform: 'Harvard/edX', url: 'https://cs50.harvard.edu/cybersecurity', free: true },
    ],
    projects: ['Home Lab Setup', 'CTF Challenges', 'Vulnerability Scanner', 'Password Manager', 'Network Monitor'],
    careers: ['Security Analyst', 'Penetration Tester', 'Security Engineer', 'SOC Analyst', 'CISO'],
  },
  'Data Science': {
    icon: '📊', color: 'from-green-500 to-emerald-600',
    description: 'Extract insights from data to drive business decisions. Data scientists are among the highest-paid professionals.',
    roadmap: [
      { phase: 'Programming', topics: ['Python', 'Pandas', 'NumPy', 'Matplotlib'], duration: '4-6 weeks' },
      { phase: 'Statistics', topics: ['Descriptive Stats', 'Probability', 'Hypothesis Testing'], duration: '4-6 weeks' },
      { phase: 'Data Analysis', topics: ['EDA', 'Data Cleaning', 'Feature Engineering'], duration: '4-6 weeks' },
      { phase: 'Machine Learning', topics: ['Regression', 'Classification', 'Clustering'], duration: '6-8 weeks' },
      { phase: 'Advanced', topics: ['Big Data', 'SQL', 'Tableau/Power BI', 'Spark'], duration: 'Ongoing' },
    ],
    courses: [
      { name: 'Kaggle Learn', platform: 'Kaggle', url: 'https://kaggle.com/learn', free: true },
      { name: 'Data Science Specialization', platform: 'Coursera', url: 'https://coursera.org', free: false },
      { name: 'DataCamp', platform: 'DataCamp', url: 'https://datacamp.com', free: false },
      { name: 'Towards Data Science', platform: 'Medium', url: 'https://towardsdatascience.com', free: true },
    ],
    projects: ['EDA on Public Dataset', 'Sales Prediction Model', 'Customer Segmentation', 'Dashboard with Tableau', 'NLP Text Analysis'],
    careers: ['Data Scientist', 'Data Analyst', 'Business Intelligence Analyst', 'ML Engineer', 'Data Engineer'],
  },
  'Mobile Development': {
    icon: '📱', color: 'from-orange-500 to-amber-600',
    description: 'Build apps for iOS and Android. Mobile apps are used by billions of people worldwide.',
    roadmap: [
      { phase: 'Basics', topics: ['UI/UX Principles', 'JavaScript/Dart', 'Git'], duration: '3-4 weeks' },
      { phase: 'Framework', topics: ['Flutter or React Native', 'Components', 'Navigation'], duration: '6-8 weeks' },
      { phase: 'Backend Integration', topics: ['REST APIs', 'Firebase', 'State Management'], duration: '4-6 weeks' },
      { phase: 'Advanced', topics: ['Animations', 'Native Modules', 'Performance'], duration: '4-6 weeks' },
      { phase: 'Publishing', topics: ['App Store', 'Play Store', 'CI/CD'], duration: '2-3 weeks' },
    ],
    courses: [
      { name: 'Flutter & Dart Complete Guide', platform: 'Udemy', url: 'https://udemy.com', free: false },
      { name: 'React Native by Meta', platform: 'Coursera', url: 'https://coursera.org', free: false },
      { name: 'Flutter Docs', platform: 'flutter.dev', url: 'https://flutter.dev/docs', free: true },
      { name: 'Expo React Native', platform: 'expo.dev', url: 'https://expo.dev', free: true },
    ],
    projects: ['Weather App', 'Todo App', 'Chat App', 'E-commerce App', 'Fitness Tracker'],
    careers: ['iOS Developer', 'Android Developer', 'Flutter Developer', 'React Native Developer', 'Mobile Architect'],
  },
  'Cloud Computing': {
    icon: '☁️', color: 'from-sky-500 to-blue-600',
    description: 'Build and manage scalable infrastructure in the cloud. Cloud skills are essential for modern software.',
    roadmap: [
      { phase: 'Cloud Basics', topics: ['Cloud Concepts', 'Virtualization', 'Networking'], duration: '3-4 weeks' },
      { phase: 'AWS/Azure/GCP', topics: ['Core Services', 'Storage', 'Compute', 'IAM'], duration: '6-8 weeks' },
      { phase: 'DevOps', topics: ['Docker', 'Kubernetes', 'CI/CD', 'Terraform'], duration: '6-8 weeks' },
      { phase: 'Security', topics: ['Cloud Security', 'Compliance', 'Monitoring'], duration: '4-6 weeks' },
      { phase: 'Certifications', topics: ['AWS SAA', 'Azure AZ-900', 'GCP ACE'], duration: 'Ongoing' },
    ],
    courses: [
      { name: 'AWS Cloud Practitioner', platform: 'AWS', url: 'https://aws.amazon.com/training', free: true },
      { name: 'Google Cloud Skills Boost', platform: 'Google', url: 'https://cloudskillsboost.google', free: true },
      { name: 'Azure Fundamentals', platform: 'Microsoft Learn', url: 'https://learn.microsoft.com', free: true },
      { name: 'Docker & Kubernetes', platform: 'Udemy', url: 'https://udemy.com', free: false },
    ],
    projects: ['Deploy Web App on AWS', 'Serverless Function', 'CI/CD Pipeline', 'Kubernetes Cluster', 'Infrastructure as Code'],
    careers: ['Cloud Engineer', 'DevOps Engineer', 'Site Reliability Engineer', 'Cloud Architect', 'Platform Engineer'],
  },
  'Game Development': {
    icon: '🎮', color: 'from-violet-500 to-purple-600',
    description: 'Create interactive games and experiences. Game development combines creativity with technical skills.',
    roadmap: [
      { phase: 'Basics', topics: ['Game Design Principles', 'C# or GDScript', 'Math for Games'], duration: '4-6 weeks' },
      { phase: 'Engine', topics: ['Unity or Godot', 'Scenes & Objects', 'Physics'], duration: '6-8 weeks' },
      { phase: '2D Games', topics: ['Sprites', 'Tilemaps', 'Animations', 'Audio'], duration: '4-6 weeks' },
      { phase: '3D Games', topics: ['3D Models', 'Lighting', 'Shaders', 'VFX'], duration: '8-10 weeks' },
      { phase: 'Publishing', topics: ['Optimization', 'Steam/App Store', 'Marketing'], duration: 'Ongoing' },
    ],
    courses: [
      { name: 'Unity Learn', platform: 'Unity', url: 'https://learn.unity.com', free: true },
      { name: 'Godot Docs & Tutorials', platform: 'godotengine.org', url: 'https://godotengine.org', free: true },
      { name: 'Brackeys YouTube', platform: 'YouTube', url: 'https://youtube.com/@Brackeys', free: true },
      { name: 'GameDev.tv', platform: 'Udemy', url: 'https://gamedev.tv', free: false },
    ],
    projects: ['Pong Clone', 'Platformer Game', 'Top-down RPG', 'Puzzle Game', 'Multiplayer Game'],
    careers: ['Game Developer', 'Game Designer', 'Unity Developer', 'Technical Artist', 'Game Producer'],
  },
  'Coding': {
    icon: '💻', color: 'from-slate-600 to-gray-700',
    description: 'Master programming fundamentals. Strong coding skills are the foundation of all software development.',
    roadmap: [
      { phase: 'Basics', topics: ['Variables & Types', 'Control Flow', 'Functions'], duration: '3-4 weeks' },
      { phase: 'Intermediate', topics: ['OOP', 'Data Structures', 'Algorithms'], duration: '6-8 weeks' },
      { phase: 'Problem Solving', topics: ['LeetCode Easy', 'Recursion', 'Sorting'], duration: '6-8 weeks' },
      { phase: 'Advanced', topics: ['Design Patterns', 'System Design', 'Complexity'], duration: '8-10 weeks' },
      { phase: 'Interview Prep', topics: ['LeetCode Medium/Hard', 'Mock Interviews', 'Projects'], duration: 'Ongoing' },
    ],
    courses: [
      { name: 'CS50 by Harvard', platform: 'edX', url: 'https://cs50.harvard.edu', free: true },
      { name: 'Python.org Tutorial', platform: 'python.org', url: 'https://docs.python.org/3/tutorial', free: true },
      { name: 'LeetCode', platform: 'LeetCode', url: 'https://leetcode.com', free: true },
      { name: 'Neetcode.io', platform: 'neetcode.io', url: 'https://neetcode.io', free: true },
    ],
    projects: ['Calculator', 'Todo App', 'Web Scraper', 'CLI Tool', 'REST API'],
    careers: ['Software Engineer', 'Backend Developer', 'Systems Programmer', 'DevOps Engineer', 'Tech Lead'],
  },
};

const LearningPath: React.FC = () => {
  const { userInterests, isAuthenticated, user } = useStore();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'roadmap' | 'courses' | 'projects' | 'careers'>('roadmap');

  useEffect(() => {
    if (!isAuthenticated) navigate('/login');
  }, [isAuthenticated, navigate]);

  if (!userInterests?.primaryInterest) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 pt-24 pb-12 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <div className="text-6xl mb-4">🎯</div>
          <h2 className="text-2xl font-bold text-slate-900 mb-3">No Learning Path Yet</h2>
          <p className="text-slate-600 mb-6">Complete the Interest Assessment first to get your personalized learning path.</p>
          <button onClick={() => navigate('/interest-check')} className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors">
            Take Interest Assessment
          </button>
        </div>
      </div>
    );
  }

  const primary = userInterests.primaryInterest;
  
  // Normalize key - find matching domain in DOMAIN_DATA
  let domainKey = Object.keys(DOMAIN_DATA).find(k => 
    k === primary // Exact match first
  );
  
  // If no exact match, try case-insensitive or partial match
  if (!domainKey) {
    domainKey = Object.keys(DOMAIN_DATA).find(k =>
      k.toLowerCase() === primary.toLowerCase()
    );
  }
  
  // Fallback to first word match for compound domains
  if (!domainKey) {
    const primaryFirstWord = primary.split(' ')[0].toLowerCase();
    domainKey = Object.keys(DOMAIN_DATA).find(k =>
      k.toLowerCase().startsWith(primaryFirstWord)
    );
  }
  
  // Last resort - default to Coding
  domainKey = domainKey || 'Coding';

  const domain = DOMAIN_DATA[domainKey];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 pt-24 pb-12">
      <div className="max-w-5xl mx-auto px-4">

        {/* Header */}
        <div className={`bg-gradient-to-r ${domain.color} rounded-2xl p-8 mb-8 text-white`}>
          <div className="flex items-start gap-6">
            <div className="text-6xl">{domain.icon}</div>
            <div className="flex-1">
              <p className="text-white/70 text-sm font-medium mb-1">Your Personalized Learning Path</p>
              <h1 className="text-3xl font-bold mb-2">{primary}</h1>
              <p className="text-white/80 leading-relaxed">{domain.description}</p>
              <div className="flex items-center gap-4 mt-4">
                <span className="bg-white/20 px-3 py-1 rounded-full text-sm font-medium">
                  🎯 {Math.round(userInterests.confidence)}% match
                </span>
                <span className="bg-white/20 px-3 py-1 rounded-full text-sm font-medium">
                  📚 {domain.roadmap.length} phases
                </span>
                <span className="bg-white/20 px-3 py-1 rounded-full text-sm font-medium">
                  💼 {domain.careers.length} career paths
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Secondary Interests */}
        {userInterests.allInterests.length > 1 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-6">
            <h3 className="font-semibold text-slate-700 mb-3 text-sm uppercase tracking-wide">Your Other Interests</h3>
            <div className="flex flex-wrap gap-2">
              {userInterests.allInterests.slice(1, 5).map((interest, i) => (
                <button
                  key={i}
                  onClick={() => navigate('/interest-check')}
                  className="px-4 py-2 bg-slate-100 text-slate-700 rounded-full text-sm font-medium hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
                >
                  {interest.domain} — {Math.round(interest.confidence * 100)}%
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 bg-white rounded-xl border border-slate-200 p-1">
          {(['roadmap', 'courses', 'projects', 'careers'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 py-2.5 rounded-lg text-sm font-semibold capitalize transition-all ${
                activeTab === tab ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {tab === 'roadmap' ? '🗺️ Roadmap' : tab === 'courses' ? '📚 Courses' : tab === 'projects' ? '🛠️ Projects' : '💼 Careers'}
            </button>
          ))}
        </div>

        {/* Roadmap Tab */}
        {activeTab === 'roadmap' && (
          <div className="space-y-4">
            {domain.roadmap.map((phase, i) => (
              <div key={i} className="bg-white rounded-2xl border border-slate-200 p-6 flex gap-5">
                <div className="flex flex-col items-center">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm bg-gradient-to-br ${domain.color}`}>
                    {i + 1}
                  </div>
                  {i < domain.roadmap.length - 1 && <div className="w-0.5 flex-1 bg-slate-200 mt-2" />}
                </div>
                <div className="flex-1 pb-2">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-bold text-slate-900 text-lg">{phase.phase}</h3>
                    <span className="text-xs text-slate-500 bg-slate-100 px-3 py-1 rounded-full">⏱ {phase.duration}</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {phase.topics.map((topic, j) => (
                      <span key={j} className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-sm font-medium">{topic}</span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
            <div className="text-center pt-4">
              <button onClick={() => navigate('/quizzes')} className="px-8 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors">
                Start with Quizzes →
              </button>
            </div>
          </div>
        )}

        {/* Courses Tab */}
        {activeTab === 'courses' && (
          <div className="grid sm:grid-cols-2 gap-4">
            {domain.courses.map((course, i) => (
              <a key={i} href={course.url} target="_blank" rel="noopener noreferrer"
                className="bg-white rounded-2xl border border-slate-200 p-6 hover:border-indigo-300 hover:shadow-md transition-all group">
                <div className="flex items-start justify-between mb-3">
                  <span className={`text-xs font-bold px-2 py-1 rounded-full ${course.free ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                    {course.free ? '✓ FREE' : '💳 PAID'}
                  </span>
                  <svg className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </div>
                <h3 className="font-bold text-slate-900 mb-1 group-hover:text-indigo-600 transition-colors">{course.name}</h3>
                <p className="text-sm text-slate-500">{course.platform}</p>
              </a>
            ))}
          </div>
        )}

        {/* Projects Tab */}
        {activeTab === 'projects' && (
          <div className="grid sm:grid-cols-2 gap-4">
            {domain.projects.map((project, i) => (
              <div key={i} className="bg-white rounded-2xl border border-slate-200 p-6 flex items-center gap-4">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${domain.color} flex items-center justify-center text-white font-bold`}>
                  {i + 1}
                </div>
                <div>
                  <h3 className="font-bold text-slate-900">{project}</h3>
                  <p className="text-sm text-slate-500">Hands-on project</p>
                </div>
              </div>
            ))}
            <div className="bg-indigo-50 rounded-2xl border border-indigo-200 p-6 flex items-center gap-4 sm:col-span-2">
              <div className="text-3xl">💡</div>
              <div>
                <h3 className="font-bold text-indigo-900">Pro Tip</h3>
                <p className="text-sm text-indigo-700">Build projects from day one. Even simple projects teach you more than tutorials alone.</p>
              </div>
            </div>
          </div>
        )}

        {/* Careers Tab */}
        {activeTab === 'careers' && (
          <div className="grid sm:grid-cols-2 gap-4">
            {domain.careers.map((career, i) => (
              <div key={i} className="bg-white rounded-2xl border border-slate-200 p-6">
                <div className="flex items-center gap-3 mb-2">
                  <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${domain.color} flex items-center justify-center text-white text-lg`}>
                    💼
                  </div>
                  <h3 className="font-bold text-slate-900">{career}</h3>
                </div>
                <p className="text-sm text-slate-500">High demand in the industry</p>
              </div>
            ))}
          </div>
        )}

        {/* Bottom CTA */}
        <div className="mt-8 bg-white rounded-2xl border border-slate-200 p-6 flex items-center justify-between">
          <div>
            <h3 className="font-bold text-slate-900">Ready to test your knowledge?</h3>
            <p className="text-sm text-slate-500 mt-1">Take quizzes tailored to your {primary} interest</p>
          </div>
          <div className="flex gap-3">
            <button onClick={() => navigate('/dashboard')} className="px-4 py-2 border border-slate-200 text-slate-700 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors">
              Dashboard
            </button>
            <button onClick={() => navigate('/quizzes')} className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors">
              Take Quiz →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LearningPath;
