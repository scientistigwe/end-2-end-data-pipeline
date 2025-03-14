import React, { useRef } from "react";
import { motion, useInView, useScroll, useTransform } from "framer-motion";
import { Link } from "react-router-dom";
import {
  ArrowRight,
  Database,
  Shield,
  Zap,
  BarChart3,
  Users,
  Twitter,
  Linkedin,
  Github,
} from "lucide-react";
import PipelineLogo from "@/assets/PipelineLogo";
import { ModeToggle } from "@/common/components/modeToggle";

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

const socialLinks = [
  { icon: Twitter, href: "https://twitter.com/enterprisepipe" },
  { icon: Linkedin, href: "https://linkedin.com/company/enterprisepipeline" },
  { icon: Github, href: "https://github.com/enterprisepipeline" },
];

const LandingPage = () => {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"]
  });

  // Parallax effect for hero background
  const backgroundY = useTransform(scrollYProgress, [0, 1], ["0%", "50%"]);
  const textY = useTransform(scrollYProgress, [0, 1], ["0%", "150%"]);

  return (
    <div className="min-h-screen bg-background overflow-x-hidden">
      {/* Navigation */}
      <motion.nav
        initial={{ opacity: 0, y: -50 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="sticky top-0 z-50 bg-card/80 backdrop-blur-md border-b border-border"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link
              to="/"
              className="flex items-center space-x-3 group"
            >
              <PipelineLogo className="h-8 w-8 group-hover:rotate-6 transition-transform" />
              <span className="font-bold text-xl text-foreground group-hover:text-primary transition-colors">
              My Assistant Data Pipeline
              </span>
            </Link>
            <div className="flex items-center space-x-4">
              <ModeToggle />
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
      </motion.nav>

      {/* Hero Section */}
      <section
        ref={ref}
        className="relative overflow-hidden pt-16 sm:pt-24 h-screen flex items-center"
      >
        <motion.div
          style={{ y: backgroundY }}
          className="absolute inset-0 bg-gradient-to-br from-primary/10 to-secondary/10 -z-10"
        />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            style={{ y: textY }}
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-foreground tracking-tight">
              Data Quality & Integration Pipeline
            </h1>
            <p className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto">
              Transform your data processing with intelligent orchestration,
              quality management, and human-centric automation
            </p>
            <div className="mt-8 flex flex-col sm:flex-row justify-center gap-4">
              <motion.div
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <Link
                  to="/register"
                  className="inline-flex items-center justify-center px-6 py-3 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors space-x-2"
                >
                  <span>Start Free Trial</span>
                  <ArrowRight className="w-4 h-4" />
                </Link>
              </motion.div>
              <motion.div
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
              >
                <Link
                  to="/demo"
                  className="inline-flex items-center justify-center px-6 py-3 bg-secondary text-secondary-foreground rounded-md hover:bg-secondary/90 transition-colors"
                >
                  Request Demo
                </Link>
              </motion.div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 sm:py-32 bg-muted/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            viewport={{ once: true }}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
          >
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                transition={{
                  duration: 0.5,
                  delay: index * 0.1
                }}
                viewport={{ once: true }}
                className="group relative rounded-lg border border-border bg-card p-6 hover:shadow-xl hover:border-primary/50 transition-all"
              >
                <div className="text-primary transition-transform group-hover:scale-110">
                  {feature.icon}
                </div>
                <h3 className="mt-4 text-xl font-semibold text-foreground">
                  {feature.title}
                </h3>
                <p className="mt-2 text-muted-foreground">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </motion.div>
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
            <div className="col-span-2 md:col-span-1">
              <h4 className="font-semibold text-foreground mb-4">Connect</h4>
              <div className="flex space-x-4">
                {socialLinks.map(({ icon: Icon, href }) => (
                  <motion.a
                    key={href}
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    whileHover={{ scale: 1.2 }}
                    whileTap={{ scale: 0.9 }}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <Icon className="w-6 h-6" />
                  </motion.a>
                ))}
              </div>
            </div>
          </div>
          <div className="mt-8 pt-8 border-t border-border flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <PipelineLogo className="h-6 w-6" />
              <span className="text-muted-foreground text-sm">
                © {new Date().getFullYear()} Analytix Flow. All rights reserved.
              </span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;