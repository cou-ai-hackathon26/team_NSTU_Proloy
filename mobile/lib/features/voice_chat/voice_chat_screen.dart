import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';
import '../emergency/emergency_screen.dart';

class VoiceChatScreen extends StatefulWidget {
  const VoiceChatScreen({super.key});

  @override
  State<VoiceChatScreen> createState() => _VoiceChatScreenState();
}

class _VoiceChatScreenState extends State<VoiceChatScreen> with SingleTickerProviderStateMixin {
  bool _isRecording = false;
  bool _isLoading = false;
  String _statusText = 'কথা বলতে বোতামে চাপ দিন';
  String _replyText = '';
  String _citations = '';
  late AnimationController _waveController;

  @override
  void initState() {
    super.initState();
    _waveController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _waveController.dispose();
    super.dispose();
  }

  Future<void> _handleVoiceQuery(String sampleQuery) async {
    setState(() {
      _isLoading = true;
      _statusText = 'ভাবছি... একটু অপেক্ষা করুন';
    });

    try {
      final res = await ShoiApiClient.post('/chat', {'message': sampleQuery});
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        setState(() {
          _replyText = data['reply'] ?? '';
          final citList = data['citations'] as List?;
          _citations = (citList != null && citList.isNotEmpty) ? citList.join(', ') : '';
          _statusText = 'কথা বলতে বোতামে চাপ দিন';
        });

        if (data['risk_level'] == 'high') {
          if (mounted) {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const EmergencyScreen()),
            );
          }
        }
      } else {
        setState(() => _statusText = 'উত্তর পাওয়া যায়নি, আবার চেষ্টা করুন');
      }
    } catch (e) {
      setState(() => _statusText = 'ইন্টারনেট সংযোগ চেক করুন');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Row(
          children: [
            Text('🌸 সই (Shoi)'),
            SizedBox(width: 8),
            Text('🔒 সম্পূর্ণ নিরাপদ', style: TextStyle(fontSize: 12, color: Colors.grey)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.emergency, color: ShoiTheme.emergencyColor),
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const EmergencyScreen()),
            ),
          )
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            children: [
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                decoration: BoxDecoration(
                  color: ShoiTheme.primaryLight,
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  _statusText,
                  style: const TextStyle(
                    color: ShoiTheme.primaryDark,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const Spacer(),
              // Big Microphone Button
              Center(
                child: GestureDetector(
                  onTap: () {
                    _handleVoiceQuery("পিরিয়ডের স্বাভাবিক চক্র কত দিনের হয়?");
                  },
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      if (_isRecording || _isLoading)
                        ScaleTransition(
                          scale: Tween(begin: 1.0, end: 1.3).animate(_waveController),
                          child: Container(
                            width: 140,
                            height: 140,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: ShoiTheme.primaryColor.withOpacity(0.2),
                            ),
                          ),
                        ),
                      Container(
                        width: 120,
                        height: 120,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: const LinearGradient(
                            colors: [ShoiTheme.primaryColor, ShoiTheme.primaryDark],
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: ShoiTheme.primaryColor.withOpacity(0.35),
                              blurRadius: 20,
                              offset: const Offset(0, 8),
                            )
                          ],
                        ),
                        child: const Icon(Icons.mic, size: 55, color: Colors.white),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 16),
              const Text(
                'বোতামটিতে চাপ দিয়ে কথা বলুন',
                style: TextStyle(color: Colors.grey, fontSize: 14),
              ),
              const Spacer(),

              // Response Card
              if (_replyText.isNotEmpty)
                Card(
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                  color: const Color(0xFFFFF9FA),
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Row(
                          children: [
                            Text('🌸 সই-এর উত্তর', style: TextStyle(fontWeight: FontWeight.bold, color: ShoiTheme.primaryDark)),
                            Spacer(),
                            Icon(Icons.volume_up, size: 18, color: ShoiTheme.primaryColor),
                          ],
                        ),
                        const SizedBox(height: 8),
                        Text(_replyText, style: const TextStyle(fontSize: 15, height: 1.4)),
                        if (_citations.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          Text('সূত্র: $_citations', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                        ]
                      ],
                    ),
                  ),
                ),

              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}
