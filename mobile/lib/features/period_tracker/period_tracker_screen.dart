import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';

class PeriodTrackerScreen extends StatefulWidget {
  const PeriodTrackerScreen({super.key});

  @override
  State<PeriodTrackerScreen> createState() => _PeriodTrackerScreenState();
}

class _PeriodTrackerScreenState extends State<PeriodTrackerScreen> {
  String _explanation = 'পূর্বাভাস দেখতে পিরিয়ড যোগ করুন';
  DateTime _selectedDate = DateTime.now();

  @override
  void initState() {
    super.initState();
    _fetchAnalysis();
  }

  Future<void> _fetchAnalysis() async {
    try {
      final res = await ShoiApiClient.get('/track/period/analysis');
      if (res.statusCode == 200) {
        final data = jsonDecode(utf8.decode(res.bodyBytes));
        setState(() {
          _explanation = data['explanation_bn'] ?? '';
        });
      }
    } catch (_) {}
  }

  Future<void> _logPeriod() async {
    final dateStr = "${_selectedDate.year}-${_selectedDate.month.toString().padLeft(2, '0')}-${_selectedDate.day.toString().padLeft(2, '0')}";
    try {
      final res = await ShoiApiClient.post('/track/period', {
        'start_date': dateStr,
        'flow': 'medium',
        'symptoms': ['তলপেটে ব্যথা']
      });
      if (res.statusCode == 200) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('পিরিয়ড সফলভাবে যোগ করা হয়েছে!')),
        );
        _fetchAnalysis();
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('🩸 মাসিক ট্র্যাকার')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            color: ShoiTheme.primaryLight,
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('চক্রের পূর্বাভাস ও পরামর্শ', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 8),
                  Text(_explanation, style: const TextStyle(fontSize: 14)),
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
                  const Text('পিরিয়ড শুরু রেকর্ড করুন', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Text('তারিখ: ${_selectedDate.day}/${_selectedDate.month}/${_selectedDate.year}'),
                      const Spacer(),
                      OutlinedButton(
                        onPressed: () async {
                          final picked = await showDatePicker(
                            context: context,
                            initialDate: _selectedDate,
                            firstDate: DateTime(2020),
                            lastDate: DateTime.now(),
                          );
                          if (picked != null) setState(() => _selectedDate = picked);
                        },
                        child: const Text('তারিখ পরিবর্তন'),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _logPeriod,
                      child: const Text('সংরক্ষণ করুন'),
                    ),
                  )
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
