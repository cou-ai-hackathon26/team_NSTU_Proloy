import 'package:flutter/material.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('⚙️ সেটিংস ও সুরক্ষা')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('গোপনীয়তার প্রতিশ্রুতি', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 8),
                  const Text('আপনার নাম, ফোন নম্বর, বা ইমেইল কখনো সংগ্রহ বা সংরক্ষণ করা হয় না। আপনার একটি এলোমেলো পরিচয় আইডি ব্যবহৃত হয়।'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('সব তথ্য মুছে ফেলুন (Wipe All Data)', style: TextStyle(fontWeight: FontWeight.bold, color: Colors.red)),
                  const SizedBox(height: 8),
                  const Text('এই ডিভাইসে এবং সার্ভারে সংরক্ষিত আপনার সমস্ত মাসিক, মেজাজ এবং স্বাস্থ্যের ইতিহাস স্থায়ীভাবে মুছে ফেলা হবে।'),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                      onPressed: () async {
                        final confirm = await showDialog<bool>(
                          context: context,
                          builder: (ctx) => AlertDialog(
                            title: const Text('সব তথ্য মুছবেন?'),
                            content: const Text('এটি আর কোনোভাবেই ফিরিয়ে আনা যাবে না।'),
                            actions: [
                              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('না')),
                              TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('হ্যাঁ, মুছে ফেলুন')),
                            ],
                          ),
                        );
                        if (confirm == true) {
                          await ShoiApiClient.delete('/auth/me');
                          await ShoiApiClient.clearAuth();
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(content: Text('আপনার সমস্ত তথ্য মুছে ফেলা হয়েছে।')),
                            );
                          }
                        }
                      },
                      child: const Text('🗑️ সমস্ত তথ্য স্থায়ীভাবে মুছুন'),
                    ),
                  )
                ],
              ),
            ),
          )
        ],
      ),
    );
  }
}
