import 'package:flutter/material.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../../main.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  bool _isLoading = false;

  Future<void> _startAnonymously() async {
    setState(() => _isLoading = true);
    try {
      final res = await ShoiApiClient.post('/auth/anonymous', {
        'age_group': '20-29',
        'language': 'bn'
      });
      if (res.statusCode == 200) {
        if (mounted) {
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(builder: (_) => const MainNavigationHolder()),
          );
        }
      }
    } catch (_) {}
    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Spacer(),
              const Text('🌸', style: TextStyle(fontSize: 72)),
              const SizedBox(height: 16),
              const Text(
                'সই (Shoi)',
                style: TextStyle(
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  color: ShoiTheme.primaryColor,
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                'গ্রামীণ ও সুবিধাবঞ্চিত নারীদের একান্ত স্বাস্থ্য ও মনের সুরক্ষার সঙ্গী।',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 16, color: Colors.grey),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: ShoiTheme.primaryLight,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Row(
                  children: [
                    Icon(Icons.lock, color: ShoiTheme.primaryDark),
                    SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'কোনো নাম, ফোন বা ইমেইল লাগবে না। আপনার তথ্য সম্পূর্ণ গোপন থাকবে।',
                        style: TextStyle(fontSize: 13, color: ShoiTheme.primaryDark),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _startAnonymously,
                  child: Text(_isLoading ? 'প্রবেশ করা হচ্ছে...' : 'শুরু করুন (সম্পূর্ণ বেনামে)'),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );
  }
}
