import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/theme.dart';

class EmergencyScreen extends StatelessWidget {
  const EmergencyScreen({super.key});

  Future<void> _makeCall(String number) async {
    final uri = Uri.parse('tel:$number');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        title: const Text('জরুরি মানসিক ও স্বাস্থ্য সহায়তা'),
        automaticallyImplyLeading: false,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              const SizedBox(height: 20),
              const Text('🕊️', style: TextStyle(fontSize: 56)),
              const SizedBox(height: 12),
              const Text(
                'আমরা আপনার পাশে আছি',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                  color: ShoiTheme.primaryDark,
                ),
              ),
              const SizedBox(height: 10),
              const Text(
                'আপনি একা নন। আপনার কষ্ট আমরা বুঝতে পারছি। যেকোনো বিপদে বা সাহায্যে সরাসরি নিচের নম্বরে যোগাযোগ করুন।',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 15, color: Colors.black87),
              ),
              const SizedBox(height: 30),

              // 999 Call Button
              SizedBox(
                width: double.infinity,
                child: ElevatedButton.icon(
                  onPressed: () => _makeCall('999'),
                  icon: const Icon(Icons.phone, color: Colors.white),
                  label: const Text('৯৯৯ এ কল করুন (জাতীয় জরুরি সেবা)'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: ShoiTheme.emergencyColor,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                ),
              ),
              const SizedBox(height: 14),

              // 109 Call Button
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () => _makeCall('109'),
                  icon: const Icon(Icons.phone_in_talk, color: ShoiTheme.primaryDark),
                  label: const Text(
                    '১০৯ এ কল করুন (নারী নির্যাতন সেল)',
                    style: TextStyle(color: ShoiTheme.primaryDark, fontWeight: FontWeight.bold),
                  ),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    side: const BorderSide(color: ShoiTheme.primaryColor),
                  ),
                ),
              ),

              const SizedBox(height: 25),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Column(
                  children: [
                    Text('🌸 মন শান্ত করার ছোট্ট পরামর্শ:', style: TextStyle(fontWeight: FontWeight.bold)),
                    SizedBox(height: 4),
                    Text('চোখ বন্ধ করে বুক ভরে ধীরে ধীরে একটি গভীর শ্বাস নিন এবং আস্তে আস্তে ছাড়ুন।'),
                  ],
                ),
              ),

              const Spacer(),
              TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('আমি এখন ঠিক আছি (ফিরে যান)', style: TextStyle(color: Colors.grey)),
              )
            ],
          ),
        ),
      ),
    );
  }
}
