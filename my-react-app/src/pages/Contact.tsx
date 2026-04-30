import React, { useState } from 'react';
import { Mail, Phone, MapPin, Send, Loader2, CheckCircle2, ArrowRight } from 'lucide-react';

const Contact: React.FC = () => {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: ''
  });
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      setSubmitted(true);
      setFormData({ name: '', email: '', subject: '', message: '' });
      setTimeout(() => setSubmitted(false), 5000);
    } catch (error) {
      console.error('Form submission error:', error);
    } finally {
      setLoading(false);
    }
  };

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
            <span className="text-indigo-300 text-xs font-semibold uppercase tracking-wider">Get in Touch</span>
          </div>
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 animate-slide-up leading-tight">
            We're Here to Help
            <span className="block bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Let's Connect
            </span>
          </h1>
          <p className="text-xl sm:text-2xl text-slate-300 max-w-3xl mx-auto animate-slide-up animation-delay-100 leading-relaxed">
            Have questions? We'd love to hear from you. Send us a message and we'll respond as soon as possible.
          </p>
        </div>
      </section>

      {/* Contact Info Cards */}
      <section className="py-20 sm:py-28 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6 sm:gap-8 mb-12">
            {[
              {
                icon: <Mail className="w-8 h-8" />,
                title: 'Email',
                content: 'support@plpg.ai',
                link: 'mailto:support@plpg.ai'
              },
              {
                icon: <Phone className="w-8 h-8" />,
                title: 'Phone',
                content: '+1 (555) 123-4567',
                link: 'tel:+15551234567'
              },
              {
                icon: <MapPin className="w-8 h-8" />,
                title: 'Address',
                content: 'San Francisco, CA',
                link: '#'
              }
            ].map((item, idx) => (
              <a
                key={idx}
                href={item.link}
                className="p-6 sm:p-8 rounded-xl border border-slate-200 hover:border-indigo-300 bg-white hover:bg-slate-50 text-center transition-all duration-300 hover-lift animate-slide-up"
                style={{ animationDelay: `${idx * 100}ms` }}
              >
                <div className="w-14 h-14 bg-indigo-100 rounded-lg flex items-center justify-center mb-4 text-indigo-600 mx-auto">
                  {item.icon}
                </div>
                <h3 className="text-xl font-semibold text-slate-900 mb-2">{item.title}</h3>
                <p className="text-base sm:text-lg text-slate-600">{item.content}</p>
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* Contact Form Section */}
      <section className="py-20 sm:py-28 bg-slate-50">
        <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="p-6 sm:p-8 md:p-12 rounded-xl border border-slate-200 bg-white shadow-lg hover:shadow-xl transition-all duration-300 animate-slide-up">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-slate-900 mb-6 sm:mb-8 leading-tight">
              Send us a Message
            </h2>
            
            {submitted && (
              <div className="mb-6 rounded-lg bg-emerald-50 border border-emerald-200 p-4 flex items-start gap-3 animate-fade-in">
                <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                <p className="text-base sm:text-lg text-emerald-700 font-medium">Thank you! Your message has been sent successfully. We'll get back to you soon.</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6">
              <div>
                <label htmlFor="contact-name" className="block text-base font-semibold text-slate-700 mb-2">Name</label>
                <input
                  id="contact-name"
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  required
                  className="w-full rounded-lg border border-slate-300 px-4 py-4 text-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-200"
                  placeholder="Your name"
                />
              </div>

              <div>
                <label htmlFor="contact-email" className="block text-base font-semibold text-slate-700 mb-2">Email</label>
                <input
                  id="contact-email"
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  required
                  className="w-full rounded-lg border border-slate-300 px-4 py-4 text-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-200"
                  placeholder="your@email.com"
                />
              </div>

              <div>
                <label htmlFor="contact-subject" className="block text-base font-semibold text-slate-700 mb-2">Subject</label>
                <input
                  id="contact-subject"
                  type="text"
                  name="subject"
                  value={formData.subject}
                  onChange={handleChange}
                  required
                  className="w-full rounded-lg border border-slate-300 px-4 py-4 text-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-200"
                  placeholder="How can we help?"
                />
              </div>

              <div>
                <label htmlFor="contact-message" className="block text-base font-semibold text-slate-700 mb-2">Message</label>
                <textarea
                  id="contact-message"
                  name="message"
                  value={formData.message}
                  onChange={handleChange}
                  required
                  rows={6}
                  className="w-full rounded-lg border border-slate-300 px-4 py-4 text-lg text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all duration-200 resize-none"
                  placeholder="Tell us more about your inquiry..."
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-8 py-4 sm:py-5 text-lg font-semibold hover:shadow-lg transform hover:scale-105 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-6 h-6 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="w-6 h-6" />
                    Send Message
                  </>
                )}
              </button>
            </form>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-20 sm:py-28 bg-white">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16 animate-slide-up">
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-slate-900 mb-4 leading-tight">
              Frequently Asked Questions
            </h2>
            <p className="text-xl sm:text-2xl text-slate-600">
              Find answers to common questions
            </p>
          </div>

          <div className="space-y-4">
            {[
              {
                q: 'How do I get started?',
                a: 'Simply create an account, take our interest assessment, and start exploring personalized learning paths tailored to your goals.'
              },
              {
                q: 'Is my data secure?',
                a: 'Yes, we use enterprise-grade encryption and security measures to protect your data. Your privacy is our top priority.'
              },
              {
                q: 'Can I export my learning data?',
                a: 'Yes, you can export your learning history and analytics from your profile settings at any time.'
              },
              {
                q: 'What payment methods do you accept?',
                a: 'We accept all major credit cards, PayPal, and bank transfers for enterprise accounts.'
              }
            ].map((faq, idx) => (
              <div
                key={idx}
                className="p-5 sm:p-6 rounded-xl border border-slate-200 bg-white hover:border-indigo-300 hover:shadow-lg transition-all duration-300 hover-lift animate-slide-up"
                style={{ animationDelay: `${idx * 100}ms` }}
              >
                <h3 className="text-lg sm:text-xl font-semibold text-slate-900 mb-2">{faq.q}</h3>
                <p className="text-base sm:text-lg text-slate-600 leading-relaxed">{faq.a}</p>
              </div>
            ))}
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
            Ready to Get Started?
          </h2>
          <p className="text-lg sm:text-xl text-indigo-100 mb-6 sm:mb-8 max-w-2xl mx-auto leading-relaxed">
            Join thousands of learners transforming their education today.
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

export default Contact;
