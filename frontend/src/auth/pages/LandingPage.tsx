import React from "react";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Database,
  Shield,
  Zap,
  BarChart3,
  Users,
} from "lucide-react";
import PipelineLogo from "@/assets/PipelineLogo";

const features = [
  {
    icon: <Database className="w-12 h-12" />,
    title: "Multi-Source Integration",
    description:
      "Seamlessly connect and process data from multiple sources with intelligent routing and validation.",
  },
  {
    icon: <Shield className="w-12 h-12" />,
    title: "Quality-First Processing",
    description:
      "Implement continuous quality assessment with strategic checkpoints and validation rules.",
  },
  {
    icon: <Zap className="w-12 h-12" />,
    title: "Advanced Orchestration",
    description:
      "Manage complex workflows with transaction integrity and comprehensive audit trails.",
  },
  {
    icon: <BarChart3 className="w-12 h-12" />,
    title: "Real-time Analytics",
    description:
      "Monitor pipeline performance, quality metrics, and business impact in real-time.",
  },
  {
    icon: <Users className="w-12 h-12" />,
    title: "User Empowerment",
    description:
      "Enable meaningful user interaction with sophisticated decision management interface.",
  },
];

const footerLinks = {
  product: ["Features", "Pricing", "Documentation"],
  company: ["About", "Contact", "Careers"],
};

const LandingPage = () => {
  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-card border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-3">
              <PipelineLogo className="h-8 w-8" />
              <span className="font-bold text-xl text-foreground">
                Enterprise Pipeline
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                to="/login"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative overflow-hidden pt-16 sm:pt-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-foreground tracking-tight">
            Data Quality & Integration Pipeline
          </h1>
          <p className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto">
            Transform your data processing with intelligent orchestration,
            quality management, and human-centric automation
          </p>
          <div className="mt-8 flex flex-col sm:flex-row justify-center gap-4">
            <Link
              to="/register"
              className="inline-flex items-center justify-center px-6 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors space-x-2"
            >
              <span>Start Free Trial</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/demo"
              className="inline-flex items-center justify-center px-6 py-3 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 transition-colors"
            >
              Request Demo
            </Link>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 sm:py-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="group relative rounded-lg border border-border bg-card p-6 hover:shadow-lg transition-shadow"
              >
                <div className="text-primary">{feature.icon}</div>
                <h3 className="mt-4 text-xl font-semibold text-foreground">
                  {feature.title}
                </h3>
                <p className="mt-2 text-muted-foreground">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-muted/40 border-t border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div>
              <h4 className="font-semibold text-foreground mb-4">Product</h4>
              <ul className="space-y-2">
                {footerLinks.product.map((link) => (
                  <li key={link}>
                    <Link
                      to={`/${link.toLowerCase()}`}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {link}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-foreground mb-4">Company</h4>
              <ul className="space-y-2">
                {footerLinks.company.map((link) => (
                  <li key={link}>
                    <Link
                      to={`/${link.toLowerCase()}`}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                    >
                      {link}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t border-border flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <PipelineLogo className="h-6 w-6" />
              <span className="text-muted-foreground text-sm">
                © 2024 Enterprise Pipeline. All rights reserved.
              </span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
