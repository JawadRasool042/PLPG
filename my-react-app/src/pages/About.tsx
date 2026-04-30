import React from 'react';
import { Users, Target, Zap, Award } from 'lucide-react';

const About: React.FC = () => {
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
            <span className="text-indigo-300 text-xs font-semibold uppercase tracking-wider">About PLPG</span>
          </div>
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 animate-slide-up leading-tight">
            Transforming Education
            <span className="block bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent pb-2.5">
              Through Innovation
            </span>
          </h1>
          <p className="text-xl sm:text-2xl text-slate-300 max-w-3xl mx-auto animate-slide-up animation-delay-100 leading-relaxed">
            We believe every learner deserves a personalized education experience. Our mission is to combine cutting-edge AI with proven pedagogical methods.
          </p>
        </div>
      </section>

      {/* Mission Section */}
      <section className="py-20 sm:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
            <div className="animate-slide-in-left">
              <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-slate-900 mb-6 leading-tight">
                Our Mission
              </h2>
              <p className="text-xl sm:text-2xl text-slate-600 leading-relaxed mb-6">
                We empower learners worldwide with AI-driven personalized education paths. By analyzing individual learning patterns, we create adaptive experiences that evolve with each student.
              </p>
              <ul className="space-y-4">
                {[
                  'Adaptive learning paths tailored to individual needs',
                  'AI-powered content recommendations',
                  'Real-time performance analytics',
                  'Community-driven learning support'
                ].map((item, idx) => (
                  <li key={idx} className="flex items-start gap-3 group animate-slide-up" style={{ animationDelay: `${idx * 100}ms` }}>
                    <div className="flex-shrink-0 mt-1">
                      <CheckIcon />
                    </div>
                    <span className="text-lg text-slate-700 group-hover:text-slate-900 transition-colors">{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="relative hidden lg:block animate-slide-in-right">
              <div className="absolute inset-0 bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-2xl opacity-20 blur-2xl"></div>
              <img
                src="https://images.unsplash.com/photo-1552664730-d307ca884978?ixlib=rb-4.0.3&auto=format&fit=crop&w=1470&q=80"
                alt="Team collaboration showing diverse professionals collaborating on educational technology"
                className="relative rounded-2xl shadow-2xl w-full h-auto object-cover"
              />
            </div>
          </div>
        </div>
      </section>

      {/* Values Section */}
      <section className="py-20 sm:py-28 bg-slate-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 animate-slide-up">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-slate-900 mb-4 leading-tight">
              Our Core Values
            </h2>
            <p className="text-xl sm:text-2xl text-slate-600 max-w-2xl mx-auto">
              Guiding principles that shape everything we do
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
            {[
              {
                icon: <Target className="w-8 h-8" />,
                title: 'Personalization',
                description: 'Every learner receives a unique, tailored experience'
              },
              {
                icon: <Zap className="w-8 h-8" />,
                title: 'Innovation',
                description: 'Continuous improvement through technology'
              },
              {
                icon: <Users className="w-8 h-8" />,
                title: 'Accessibility',
                description: 'Quality education for everyone, everywhere'
              },
              {
                icon: <Award className="w-8 h-8" />,
                title: 'Excellence',
                description: 'Highest standards in content and delivery'
              }
            ].map((value, idx) => (
              <div
                key={idx}
                className="p-6 sm:p-8 rounded-xl border border-slate-200 bg-white hover:border-indigo-300 hover:shadow-lg transition-all duration-300 hover-lift animate-slide-up"
                style={{ animationDelay: `${idx * 100}ms` }}
              >
                <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4 text-indigo-600">
                  {value.icon}
                </div>
                <h3 className="text-xl font-semibold text-slate-900 mb-2">{value.title}</h3>
                <p className="text-slate-600 text-base leading-relaxed">{value.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Team Section */}
      <section className="py-20 sm:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 animate-slide-up">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-slate-900 mb-4 leading-tight">
              Our Team
            </h2>
            <p className="text-xl sm:text-2xl text-slate-600 max-w-2xl mx-auto">
              Passionate educators, engineers, and learning scientists
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-8 mb-12">
            {[
              { label: 'Team Members', value: '25+' },
              { label: 'Years of Experience', value: '150+' },
              { label: 'Countries Served', value: '45+' }
            ].map((stat, idx) => (
              <div
                key={idx}
                className="p-6 sm:p-8 rounded-xl border border-slate-200 bg-slate-50 text-center hover:border-indigo-300 hover:shadow-lg transition-all duration-300 hover-lift animate-slide-up"
                style={{ animationDelay: `${idx * 100}ms` }}
              >
                <div className="text-4xl sm:text-5xl font-bold text-indigo-600 mb-2">{stat.value}</div>
                <div className="text-base sm:text-lg text-slate-600">{stat.label}</div>
              </div>
            ))}
          </div>

          <div className="p-6 sm:p-8 rounded-xl border border-slate-200 bg-slate-50 hover:border-indigo-300 hover:shadow-lg transition-all duration-300 hover-lift animate-slide-up animation-delay-300">
            <p className="text-lg sm:text-xl text-slate-700 leading-relaxed">
              PLPG is built by a dedicated team of educators, engineers, and learning scientists passionate about transforming education. With expertise in machine learning, pedagogy, and user experience, we're committed to creating the most effective personalized learning platform.
            </p>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-20 sm:py-28 bg-gradient-to-r from-indigo-600 to-purple-600 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute top-0 right-0 w-96 h-96 bg-white rounded-full mix-blend-multiply filter blur-3xl animate-blob"></div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="text-center mb-16 animate-slide-up">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-white mb-4 leading-tight">
              By The Numbers
            </h2>
            <p className="text-xl sm:text-2xl text-indigo-100">
              Our impact on learners worldwide
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-8">
            {[
              { number: '50K+', label: 'Active Learners' },
              { number: '1000+', label: 'Learning Paths' },
              { number: '99.9%', label: 'Uptime' }
            ].map((stat, idx) => (
              <div
                key={idx}
                className="text-center p-6 sm:p-8 rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 hover:bg-white/20 transition-all duration-300 hover-lift animate-slide-up"
                style={{ animationDelay: `${idx * 100}ms` }}
              >
                <div className="text-5xl sm:text-6xl font-bold text-white mb-2">{stat.number}</div>
                <div className="text-base sm:text-lg text-indigo-100">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

const CheckIcon = () => (
  <svg className="w-6 h-6 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
  </svg>
);

export default About;
