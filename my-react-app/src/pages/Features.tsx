import React from 'react';
import { Zap, BarChart3, Users, BookOpen, Shield, Sparkles, CheckCircle2, Gauge, ArrowRight } from 'lucide-react';

const Features: React.FC = () => {
  const features = [
    {
      icon: <Zap className="w-6 h-6" />,
      title: 'Adaptive Quizzes',
      description: 'Difficulty adjusts based on your performance'
    },
    {
      icon: <Sparkles className="w-6 h-6" />,
      title: 'Interest Assessment',
      description: 'Discover your learning interests'
    },
    {
      icon: <BarChart3 className="w-6 h-6" />,
      title: 'Progress Analytics',
      description: 'Track your learning journey'
    },
    {
      icon: <Users className="w-6 h-6" />,
      title: 'Personalized Paths',
      description: 'Custom learning based on your goals'
    },
    {
      icon: <BookOpen className="w-6 h-6" />,
      title: 'Rich Content',
      description: 'Curated materials and resources'
    },
    {
      icon: <Shield className="w-6 h-6" />,
      title: 'Enterprise Security',
      description: 'End-to-end encryption and RBAC'
    },
    {
      icon: <Gauge className="w-6 h-6" />,
      title: 'Performance Metrics',
      description: 'Detailed performance insights'
    },
    {
      icon: <CheckCircle2 className="w-6 h-6" />,
      title: 'Certifications',
      description: 'Earn recognized credentials'
    }
  ];

  return (
    <div className="min-h-screen bg-white">
      {/* Navigation Spacer */}
      <div className="h-16" />

      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 overflow-hidden py-20 sm:py-32">
        <div className="absolute inset-0 overflow-hidden">
          <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500 rounded-full mix-blend-screen filter blur-3xl opacity-10 animate-blob"></div>
          <div className="absolute bottom-0 left-0 w-96 h-96 bg-purple-500 rounded-full mix-blend-screen filter blur-3xl opacity-10 animate-blob animation-delay-2000"></div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative text-center">
          <div className="inline-flex items-center px-3 py-1 bg-indigo-500/10 border border-indigo-500/30 rounded-full mb-6 animate-fade-in">
            <span className="text-indigo-300 text-xs font-semibold uppercase tracking-wider">Platform Features</span>
          </div>
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 animate-slide-up leading-tight">
            Everything You Need
            <span className="block bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              To Succeed
            </span>
          </h1>
          <p className="text-xl sm:text-2xl text-slate-300 max-w-3xl mx-auto animate-slide-up animation-delay-100 leading-relaxed">
            Powerful features designed to accelerate your learning journey and help you achieve your goals
          </p>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 sm:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
            {features.map((feature, idx) => (
              <div
                key={idx}
                className="p-5 sm:p-6 rounded-xl border border-slate-200 hover:border-indigo-300 bg-white hover:bg-slate-50 transition-all duration-300 hover-lift animate-slide-up"
                style={{ animationDelay: `${idx * 50}ms` }}
              >
                <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4 text-indigo-600 transition-colors">
                  {feature.icon}
                </div>
                <h3 className="text-lg sm:text-xl font-semibold text-slate-900 mb-2">{feature.title}</h3>
                <p className="text-slate-600 text-base leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Detailed Features */}
      <section className="py-20 sm:py-28 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="space-y-16 sm:space-y-20 lg:space-y-24">
            {/* Adaptive Learning Engine */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center animate-slide-up">
              <div>
                <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-slate-900 mb-4 sm:mb-6 leading-tight">
                  Adaptive Learning Engine
                </h2>
                <p className="text-lg sm:text-xl text-slate-600 leading-relaxed mb-4 sm:mb-6">
                  Our AI-powered engine analyzes your performance in real-time and adjusts content difficulty to match your learning level. This ensures you're always challenged but never overwhelmed.
                </p>
                <ul className="space-y-3 sm:space-y-4">
                  {[
                    'Real-time difficulty adjustment',
                    'Personalized content recommendations',
                    'Learning style detection'
                  ].map((item, idx) => (
                    <li key={idx} className="flex items-center gap-3">
                      <CheckCircle2 className="w-5 h-5 text-indigo-600 flex-shrink-0" />
                      <span className="text-base sm:text-lg text-slate-700">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="relative hidden lg:block">
                <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-2xl opacity-20 blur-2xl"></div>
                <img
                  src="https://images.unsplash.com/photo-1552664730-d307ca884978?ixlib=rb-4.0.3&auto=format&fit=crop&w=1470&q=80"
                  alt="Adaptive learning technology showing AI-powered personalized education interface"
                  className="relative rounded-2xl shadow-lg w-full h-auto object-cover"
                />
              </div>
            </div>

            {/* Comprehensive Analytics */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center animate-slide-up animation-delay-200">
              <div className="relative hidden lg:block order-2 lg:order-1">
                <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-2xl opacity-20 blur-2xl"></div>
                <img
                  src="https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&auto=format&fit=crop&w=1470&q=80"
                  alt="Analytics dashboard displaying comprehensive learning progress metrics and insights"
                  className="relative rounded-2xl shadow-lg w-full h-auto object-cover"
                />
              </div>
              <div className="order-1 lg:order-2">
                <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-slate-900 mb-4 sm:mb-6 leading-tight">
                  Comprehensive Analytics
                </h2>
                <p className="text-lg sm:text-xl text-slate-600 leading-relaxed mb-4 sm:mb-6">
                  Get detailed insights into your learning progress with comprehensive dashboards. Track performance, identify strengths and weaknesses, and monitor your learning velocity.
                </p>
                <ul className="space-y-3 sm:space-y-4">
                  {[
                    'Performance dashboards',
                    'Learning velocity tracking',
                    'Comparative analytics'
                  ].map((item, idx) => (
                    <li key={idx} className="flex items-center gap-3">
                      <CheckCircle2 className="w-5 h-5 text-indigo-600 flex-shrink-0" />
                      <span className="text-base sm:text-lg text-slate-700">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Enterprise Security */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center animate-slide-up animation-delay-400">
              <div>
                <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-slate-900 mb-4 sm:mb-6 leading-tight">
                  Enterprise Security
                </h2>
                <p className="text-lg sm:text-xl text-slate-600 leading-relaxed mb-4 sm:mb-6">
                  Your data security is our top priority. We implement enterprise-grade security measures including end-to-end encryption, role-based access control, and comprehensive audit logging.
                </p>
                <ul className="space-y-3 sm:space-y-4">
                  {[
                    'End-to-end encryption',
                    'Role-based access control',
                    'Audit logging and compliance'
                  ].map((item, idx) => (
                    <li key={idx} className="flex items-center gap-3">
                      <CheckCircle2 className="w-5 h-5 text-indigo-600 flex-shrink-0" />
                      <span className="text-base sm:text-lg text-slate-700">{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="relative hidden lg:block">
                <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-2xl opacity-20 blur-2xl"></div>
                <img
                  src="https://images.unsplash.com/photo-1563986768609-322da13575f3?ixlib=rb-4.0.3&auto=format&fit=crop&w=1470&q=80"
                  alt="Enterprise security infrastructure with encryption and access control systems"
                  className="relative rounded-2xl shadow-lg w-full h-auto object-cover"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 sm:py-28 bg-gradient-to-r from-indigo-600 to-purple-600 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full mix-blend-multiply filter blur-3xl animate-blob"></div>
        </div>

        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 relative text-center animate-slide-up">
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-4 sm:mb-6 leading-tight">
            Experience the Difference
          </h2>
          <p className="text-lg sm:text-xl text-indigo-100 mb-6 sm:mb-8 max-w-2xl mx-auto leading-relaxed">
            Start your personalized learning journey today and unlock your full potential.
          </p>
          <a
            href="/register"
            className="inline-flex items-center px-6 sm:px-8 py-4 sm:py-5 bg-white text-indigo-600 text-lg font-semibold rounded-lg hover:shadow-lg transform hover:scale-105 transition-all duration-300 focus:ring-2 focus:ring-white focus:ring-offset-2 focus:ring-offset-indigo-600"
          >
            Get Started Free
            <ArrowRight className="ml-2 w-6 h-6" />
          </a>
        </div>
      </section>
    </div>
  );
};

export default Features;
