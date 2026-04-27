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
      title: 'RS Memorial School',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF0E4D92),
        ),
        useMaterial3: true,
      ),
      home: const SplashScreen(),
    );
  }
}

//////////////////// SPLASH ////////////////////

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  static const _brand = "RS Memorial School";

  late AnimationController _controller;
  late Animation<double> _fade;
  late Animation<double> _scale;
  late Animation<int> _textAnim;

  @override
  void initState() {
    super.initState();

    _controller =
        AnimationController(vsync: this, duration: const Duration(seconds: 2));

    _fade = CurvedAnimation(parent: _controller, curve: Curves.easeIn);
    _scale =
        Tween(begin: 0.9, end: 1.0).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutBack));

    _textAnim = StepTween(begin: 0, end: _brand.length).animate(_controller);

    _controller.forward();

    Timer(const Duration(seconds: 3), () {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => const BranchSelectionScreen()),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: AnimatedBuilder(
          animation: _controller,
          builder: (_, __) {
            return Opacity(
              opacity: _fade.value,
              child: Transform.scale(
                scale: _scale.value,
                child: Text(
                  _brand.substring(0, _textAnim.value),
                  style: const TextStyle(
                    fontSize: 36,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF0E4D92),
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

//////////////////// BRANCH SELECTION ////////////////////

class BranchSelectionScreen extends StatelessWidget {
  const BranchSelectionScreen({super.key});

  final List<Map<String, String>> branches = const [
    {
      "name": "Main Branch",
      "subtitle": "RS Memorial Public School",
      "staffUrl": "https://erp.rsmemorialpublicschool.com/login.html",
      "parentUrl": "https://erp.rsmemorialpublicschool.com/parent-login",
    },
    {
      "name": "Krish Icon",
      "subtitle": "RS Memorial Krish Icon",
      "staffUrl": "https://krish-icon.rsmemorialpublicschool.com/login.html",
      "parentUrl": "https://krish-icon.rsmemorialpublicschool.com/parent-login",
    },
    {
      "name": "Krish Star",
      "subtitle": "RS Memorial Krish Star THD",
      "staffUrl": "https://krish-star-thd.rsmemorialpublicschool.com/login.html",
      "parentUrl": "https://krish-star-thd.rsmemorialpublicschool.com/parent-login",
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Select Branch")),
      body: ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: branches.length,
        itemBuilder: (_, index) {
          final branch = branches[index];

          return GestureDetector(
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => RoleSelectionScreen(
                    branchName: branch["name"]!,
                    staffUrl: branch["staffUrl"]!,
                    parentUrl: branch["parentUrl"]!,
                  ),
                ),
              );
            },
            child: Container(
              margin: const EdgeInsets.only(bottom: 16),
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(18),
                gradient: const LinearGradient(
                  colors: [Color(0xFF0E4D92), Color(0xFF1E88E5)],
                ),
                boxShadow: [
                  BoxShadow(
                    blurRadius: 8,
                    color: Colors.black.withOpacity(0.1),
                  )
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    branch["name"]!,
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 20,
                        fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    branch["subtitle"]!,
                    style: const TextStyle(color: Colors.white70),
                  )
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}

//////////////////// ROLE SELECTION ////////////////////

class RoleSelectionScreen extends StatelessWidget {
  final String staffUrl;
  final String parentUrl;
  final String branchName;

  const RoleSelectionScreen({
    super.key,
    required this.staffUrl,
    required this.parentUrl,
    required this.branchName,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(branchName)),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          children: [
            const Spacer(),
            const Text(
              "Select Your Role",
              style: TextStyle(fontSize: 26, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 40),

            _btn(
              "Staff Login",
              Icons.school,
              true,
              () => _open(context, "Staff Login", staffUrl),
            ),

            const SizedBox(height: 16),

            _btn(
              "Parent Login",
              Icons.people,
              false,
              () => _open(context, "Parent Login", parentUrl),
            ),

            const Spacer(),
          ],
        ),
      ),
    );
  }

  Widget _btn(String text, IconData icon, bool primary, VoidCallback onTap) {
    return SizedBox(
      width: double.infinity,
      height: 60,
      child: ElevatedButton.icon(
        icon: Icon(icon),
        label: Text(text),
        onPressed: onTap,
        style: ElevatedButton.styleFrom(
          backgroundColor:
              primary ? const Color(0xFF0E4D92) : Colors.white,
          foregroundColor:
              primary ? Colors.white : const Color(0xFF0E4D92),
          side: primary
              ? BorderSide.none
              : const BorderSide(color: Color(0xFF0E4D92)),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16)),
        ),
      ),
    );
  }

  void _open(BuildContext context, String title, String url) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => WebPortalScreen(title: title, url: url),
      ),
    );
  }
}

//////////////////// WEBVIEW ////////////////////

class WebPortalScreen extends StatefulWidget {
  final String title;
  final String url;

  const WebPortalScreen({super.key, required this.title, required this.url});

  @override
  State<WebPortalScreen> createState() => _WebPortalScreenState();
}

class _WebPortalScreenState extends State<WebPortalScreen> {
  late WebViewController _controller;
  bool loading = true;

  @override
  void initState() {
    super.initState();

    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) => setState(() => loading = true),
          onPageFinished: (_) => setState(() => loading = false),
        ),
      )
      ..loadRequest(Uri.parse(widget.url));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.title),
      ),
      body: Stack(
        children: [
          WebViewWidget(controller: _controller),
          if (loading)
            const Center(child: CircularProgressIndicator()),
        ],
      ),
    );
  }
}