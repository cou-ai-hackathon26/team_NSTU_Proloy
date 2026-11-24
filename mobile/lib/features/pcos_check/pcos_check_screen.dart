import 'dart:convert';
import 'package:flutter/material.dart';
import '../../core/api_client.dart';
import '../../core/theme.dart';

class PcosCheckScreen extends StatefulWidget {
  const PcosCheckScreen({super.key});

  @override
  State<PcosCheckScreen> createState() => _PcosCheckScreenState();
}

class _PcosCheckScreenState extends State<PcosCheckScreen> {
  final _ageController = TextEditingController(text: '23');
  final _heightController = TextEditingController(text: '155');
  final _weightController = TextEditingController(text: '56');
  bool _isIrregular = false;
  bool _hasExcessHair = false;
  bool _hasWeightGain = false;

  Map<String, dynamic>? _result;
  bool _isLoading = false;

  Future<void> _checkPcos() async {
    setState(() => _isLoading = true);
    try {
      final res = await ShoiApiClient.post('/pcos/predict', {
        'age': int.tryParse(_ageController.text) ?? 23,
        'height_cm': double.tryParse(_heightController.text) ?? 155,
        'weight_kg': double.tryParse(_weightController.text) ?? 56,
        'cycle_regularity': _isIrregular ? 'irregular' : 'regular',
        'cycle_length_days': _isIrregular ? 40 : 28,
        'excess_hair_growth': _hasExcessHair,
        'weight_gain': _hasWeightGain,
        'skin_darkening': false,
        'hair_loss': false,
        'pimples_acne': false,
        'regular_exercise': false,
      });

      if (res.statusCode == 200) {
        setState(() {
          _result = jsonDecode(utf8.decode(res.bodyBytes));
        });
      }
    } catch (_) {}
    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('🩺 পিসিওএস স্ক্রিনিং')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_result == null) ...[
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('প্রাথমিক তথ্য দিন', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _ageController,
                      decoration: const InputDecoration(labelText: 'আপনার বয়স (বছর)'),
                      keyboardType: TextInputType.number,
                    ),
                    Row(
                      children: [
                        Expanded(
                          child: TextField(
                            controller: _heightController,
                            decoration: const InputDecoration(labelText: 'উচ্চতা (সেমি)'),
                            keyboardType: TextInputType.number,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextField(
                            controller: _weightController,
                            decoration: const InputDecoration(labelText: 'ওজন (কেজি)'),
                            keyboardType: TextInputType.number,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    CheckboxListTile(
                      title: const Text('পিরিয়ড প্রায়ই অনিয়মিত হয়'),
                      value: _isIrregular,
                      onChanged: (v) => setState(() => _isIrregular = v ?? false),
                    ),
                    CheckboxListTile(
                      title: const Text('চিবুকে বা মুখে অতিরিক্ত লোম রয়েছে'),
                      value: _hasExcessHair,
                      onChanged: (v) => setState(() => _hasExcessHair = v ?? false),
                    ),
                    CheckboxListTile(
                      title: const Text('সাম্প্রতিক সময়ে হঠাৎ দ্রুত ওজন বেড়েছে'),
                      value: _hasWeightGain,
                      onChanged: (v) => setState(() => _hasWeightGain = v ?? false),
                    ),
                    const SizedBox(height: 20),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _isLoading ? null : _checkPcos,
                        child: Text(_isLoading ? 'যাচাই করা হচ্ছে...' : 'ঝুঁকি যাচাই করুন'),
                      ),
                    )
                  ],
                ),
              ),
            ),
          ] else ...[
            Card(
              color: ShoiTheme.primaryLight,
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'ফলাফল: ${_result!['risk_band_bn']}',
                      style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18, color: ShoiTheme.primaryDark),
                    ),
                    const SizedBox(height: 8),
                    Text(_result!['explanation_bn'], style: const TextStyle(fontSize: 14)),
                    const SizedBox(height: 12),
                    const Text('করণীয়:', style: TextStyle(fontWeight: FontWeight.bold)),
                    ...?(_result!['actionable_advice_bn'] as List?)?.map((a) => Text('• $a')),
                    const SizedBox(height: 12),
                    Text(_result!['disclaimer_bn'], style: const TextStyle(fontSize: 12, color: Colors.grey)),
                    const SizedBox(height: 16),
                    OutlinedButton(
                      onPressed: () => setState(() => _result = null),
                      child: const Text('আবার পরীক্ষা করুন'),
                    )
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
