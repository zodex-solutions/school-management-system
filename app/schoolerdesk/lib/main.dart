import 'dart:async';

import 'package:flutter/material.dart';
import 'package:webview_flutter/webview_flutter.dart';

void main() {
  runApp(const SchoolerDeskApp());
}

class SchoolerDeskApp extends StatelessWidget {
  const SchoolerDeskApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SchoolerDesk',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        scaffoldBackgroundColor: Colors.white,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0E4D92),
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const SplashScreen(),
    );
  }
}

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  static const _brandName = 'SchoolerDesk';

  late final AnimationController _controller;
  late final Animation<double> _fadeAnimation;
  late final Animation<double> _scaleAnimation;
  late final Animation<int> _textCountAnimation;
  Timer? _navigationTimer;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1800),
    );

    _fadeAnimation = CurvedAnimation(parent: _controller, curve: Curves.easeIn);
    _scaleAnimation = Tween<double>(
      begin: 0.94,
      end: 1,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutBack));
    _textCountAnimation = StepTween(
      begin: 0,
      end: _brandName.length,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOut));

    _controller.forward();
    _navigationTimer = Timer(const Duration(milliseconds: 2800), () {
      if (!mounted) {
        return;
      }

      Navigator.of(context).pushReplacement(
        MaterialPageRoute<void>(builder: (_) => const RoleSelectionScreen()),
      );
    });
  }

  @override
  void dispose() {
    _navigationTimer?.cancel();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: AnimatedBuilder(
          animation: _controller,
          builder: (context, child) {
            final visibleCharacters = _textCountAnimation.value.clamp(
              0,
              _brandName.length,
            );

            return Opacity(
              opacity: _fadeAnimation.value,
              child: Transform.scale(
                scale: _scaleAnimation.value,
                child: Text(
                  _brandName.substring(0, visibleCharacters),
                  style: const TextStyle(
                    color: Color(0xFF0E4D92),
                    fontSize: 38,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.1,
                  ),
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class RoleSelectionScreen extends StatelessWidget {
  const RoleSelectionScreen({super.key});

  static const String staffUrl = 'https://erp.rsmemorialpublicschool.com/login.html';
  static const String parentUrl = 'https://erp.rsmemorialpublicschool.com/parent-login';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(),
              const Text(
                'Welcome to SchoolerDesk',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 30,
                  fontWeight: FontWeight.w800,
                  color: Color(0xFF0E4D92),
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Choose your login portal to continue.',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 16, color: Color(0xFF5B6472)),
              ),
              const SizedBox(height: 48),
              _LoginButton(
                label: 'Staff Login',
                onTap: () =>
                    _openPortal(context, title: 'Staff Login', url: staffUrl),
              ),
              const SizedBox(height: 16),
              _LoginButton(
                label: 'Parent Login',
                isPrimary: false,
                onTap: () =>
                    _openPortal(context, title: 'Parent Login', url: parentUrl),
              ),
              const Spacer(),
            ],
          ),
        ),
      ),
    );
  }

  void _openPortal(
    BuildContext context, {
    required String title,
    required String url,
  }) {
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => WebPortalScreen(title: title, url: url),
      ),
    );
  }
}

class _LoginButton extends StatelessWidget {
  const _LoginButton({
    required this.label,
    required this.onTap,
    this.isPrimary = true,
  });

  final String label;
  final VoidCallback onTap;
  final bool isPrimary;

  @override
  Widget build(BuildContext context) {
    final backgroundColor = isPrimary ? const Color(0xFF0E4D92) : Colors.white;
    final foregroundColor = isPrimary ? Colors.white : const Color(0xFF0E4D92);

    return SizedBox(
      height: 58,
      child: ElevatedButton(
        onPressed: onTap,
        style: ElevatedButton.styleFrom(
          backgroundColor: backgroundColor,
          foregroundColor: foregroundColor,
          elevation: isPrimary ? 0 : 0,
          side: isPrimary
              ? BorderSide.none
              : const BorderSide(color: Color(0xFF0E4D92), width: 1.5),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
          ),
        ),
        child: Text(
          label,
          style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
        ),
      ),
    );
  }
}

class WebPortalScreen extends StatefulWidget {
  const WebPortalScreen({super.key, required this.title, required this.url});

  final String title;
  final String url;

  @override
  State<WebPortalScreen> createState() => _WebPortalScreenState();
}

class _WebPortalScreenState extends State<WebPortalScreen> {
  late final WebViewController _controller;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            if (mounted) {
              setState(() {
                _isLoading = true;
              });
            }
          },
          onPageFinished: (_) {
            if (mounted) {
              setState(() {
                _isLoading = false;
              });
            }
          },
        ),
      )
      ..loadRequest(Uri.parse(widget.url));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.title), centerTitle: true),
      body: Stack(
        children: [
          WebViewWidget(controller: _controller),
          if (_isLoading) const Center(child: CircularProgressIndicator()),
        ],
      ),
    );
  }
}
