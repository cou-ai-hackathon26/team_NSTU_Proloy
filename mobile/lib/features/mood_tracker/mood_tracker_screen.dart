import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';

class MoodTrackerScreen extends StatefulWidget {
  const MoodTrackerScreen({super.key});

  @override
  State<MoodTrackerScreen> createState() => _MoodTrackerScreenState();
}

class _MoodTrackerScreenState extends State<MoodTrackerScreen> {
  int _selectedScore = 3;
  String _suggestion = 'আজ আপনার মন কেমন? নিজের অনুভূতি লিখুন।';

  final List<Map<String, dynamic>> _emojis = [
    {'score': 5, 'emoji': '🤩', 'label': 'দারুণ'},
    {'score': 4, 'emoji': '😊', 'label': 'ভালো'},
    {'score': 3, 'emoji': '😐', 'label': 'স্বাভাবিক'},
    {'score': 2, 'emoji': '😔', 'label': 'মন খারাপ'},
    {'score': 1, 'emoji': '😢', 'label': 'খুব খারাপ'},
  ];

  Future<void> _saveMood() async {
    try {
      final res = await ShoiApiClient.post('/track/mood', {
        'mood_score': _selectedScore,
        'tags': ['দৈনন্দিন লগ']
      });
      if (res.statusCode == 200) {
        _fetchAnalysis();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('আপনার অনুভূতি সংরক্ষিত হয়েছে!')),
        );
      }
    } catch (_) {}
  }

  Future<void> _fetchAnalysis() async {
    try {
      final res = await ShoiApiClient.get('/track/mood/analysis');
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        setState(() {
          _suggestion = data['gentle_suggestion_bn'] ?? '';
        });
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('😊 মনের যত্ন')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('আজকের অনুভূতি নির্বাচন করুন', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: _emojis.map((item) {
                      final isSelected = _selectedScore == item['score'];
                      return GestureDetector(
                        onTap: () => setState(() => _selectedScore = item['score']),
                        child: Container(
                          padding: const EdgeInsets.all(8),
                          decoration: BoxDecoration(
                            color: isSelected ? ShoiTheme.primaryLight : Colors.transparent,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: isSelected ? ShoiTheme.primaryColor : Colors.transparent,
                            ),
                          ),
                          child: Column(
                            children: [
                              Text(item['emoji'], style: const TextStyle(fontSize: 32)),
                              const SizedBox(height: 4),
                              Text(item['label'], style: const TextStyle(fontSize: 12)),
                            ],
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 20),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _saveMood,
                      child: const Text('সংরক্ষণ করুন'),
                    ),
                  )
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            color: const Color(0xFFF9FBF9),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('পরামর্শ', style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Text(_suggestion, style: const TextStyle(fontSize: 14)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
