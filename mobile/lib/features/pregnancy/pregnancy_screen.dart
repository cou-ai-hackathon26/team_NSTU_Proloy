import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';

class PregnancyScreen extends StatefulWidget {
  const PregnancyScreen({super.key});

  @override
  State<PregnancyScreen> createState() => _PregnancyScreenState();
}

class _PregnancyScreenState extends State<PregnancyScreen> {
  DateTime _lmp = DateTime.now().subtract(const Duration(days: 60));
  Map<String, dynamic>? _status;

  @override
  void initState() {
    super.initState();
    _fetchTimeline();
  }

  Future<void> _fetchTimeline() async {
    try {
      final res = await ShoiApiClient.get('/preg/timeline');
      if (res.statusCode == 200) {
        setState(() {
          _status = jsonDecode(utf8.decode(res.bodyBytes));
        });
      }
    } catch (_) {}
  }

  Future<void> _saveLmp() async {
    final dateStr = "${_lmp.year}-${_lmp.month.toString().padLeft(2, '0')}-${_lmp.day.toString().padLeft(2, '0')}";
    try {
      final res = await ShoiApiClient.post('/preg/start', {'lmp_date': dateStr});
      if (res.statusCode == 200) {
        setState(() {
          _status = jsonDecode(utf8.decode(res.bodyBytes));
        });
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('🤰 গর্ভকালীন যত্ন')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('শেষ মাসিকের প্রথম দিন (LMP)', style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Text('${_lmp.day}/${_lmp.month}/${_lmp.year}'),
                      const Spacer(),
                      OutlinedButton(
                        onPressed: () async {
                          final picked = await showDatePicker(
                            context: context,
                            initialDate: _lmp,
                            firstDate: DateTime.now().subtract(const Duration(days: 300)),
                            lastDate: DateTime.now(),
                          );
                          if (picked != null) setState(() => _lmp = picked);
                        },
                        child: const Text('তারিখ বাছুন'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _saveLmp,
                      child: const Text('গর্ভকাল হিসাব করুন'),
                    ),
                  )
                ],
              ),
            ),
          ),
          if (_status != null) ...[
            const SizedBox(height: 16),
            Card(
              color: ShoiTheme.primaryLight,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Text('বর্তমান বয়স: ${_status!['gestational_weeks']} সপ্তাহ', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
                    Text('ত্রৈমাসিক: ${_status!['current_trimester']}ম | সম্ভাব্য প্রসব: ${_status!['edd']}'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('শিশুর আকার: ${_status!['current_milestone']['baby_size_bn']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 8),
                    Text(_status!['current_milestone']['development_summary_bn']),
                    const SizedBox(height: 8),
                    Text(_status!['current_milestone']['maternal_changes_bn']),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              color: const Color(0xFFFFF0F0),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('⚠️ ৫টি মারাত্মক বিপদচিহ্ন', style: TextStyle(fontWeight: FontWeight.bold, color: ShoiTheme.emergencyColor)),
                    const SizedBox(height: 8),
                    ...?(_status!['current_milestone']['urgent_warning_signs_bn'] as List?)?.map((s) => Text('• $s')),
                  ],
                ),
              ),
            ),
          ]
        ],
      ),
    );
  }
}
