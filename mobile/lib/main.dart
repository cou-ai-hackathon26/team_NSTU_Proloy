import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'core/theme.dart';
import 'features/onboarding/onboarding_screen.dart';
import 'features/voice_chat/voice_chat_screen.dart';
import 'features/period_tracker/period_tracker_screen.dart';
import 'features/mood_tracker/mood_tracker_screen.dart';
import 'features/pcos_check/pcos_check_screen.dart';
import 'features/pregnancy/pregnancy_screen.dart';
import 'features/settings/settings_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ShoiApp());
}

class ShoiApp extends StatelessWidget {
  const ShoiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Shoi (সই)',
      debugShowCheckedModeBanner: false,
      theme: ShoiTheme.lightTheme,
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: const [
        Locale('bn', 'BD'),
        Locale('en', 'US'),
      ],
      home: const MainNavigationHolder(),
    );
  }
}

class MainNavigationHolder extends StatefulWidget {
  const MainNavigationHolder({super.key});

  @override
  State<MainNavigationHolder> createState() => _MainNavigationHolderState();
}

class _MainNavigationHolderState extends State<MainNavigationHolder> {
  int _currentIndex = 0;

  final List<Widget> _screens = const [
    VoiceChatScreen(),
    PeriodTrackerScreen(),
    MoodTrackerScreen(),
    PcosCheckScreen(),
    PregnancyScreen(),
    SettingsScreen(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: _screens[_currentIndex],
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        type: BottomNavigationBarType.fixed,
        selectedItemColor: ShoiTheme.primaryColor,
        unselectedItemColor: Colors.grey,
        selectedLabelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
        unselectedLabelStyle: const TextStyle(fontSize: 11),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.mic), label: 'কণ্ঠ'),
          BottomNavigationBarItem(icon: Icon(Icons.water_drop), label: 'মাসিক'),
          BottomNavigationBarItem(icon: Icon(Icons.sentiment_satisfied_alt), label: 'মেজাজ'),
          BottomNavigationBarItem(icon: Icon(Icons.health_and_safety), label: 'পিসিওএস'),
          BottomNavigationBarItem(icon: Icon(Icons.pregnant_woman), label: 'গর্ভকাল'),
          BottomNavigationBarItem(icon: Icon(Icons.settings), label: 'সেটিংস'),
        ],
      ),
    );
  }
}
