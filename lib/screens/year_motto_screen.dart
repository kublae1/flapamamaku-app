import 'package:flutter/material.dart';

class YearMottoScreen extends StatelessWidget {
  const YearMottoScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Jahresmotto')),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          AspectRatio(
            aspectRatio: 4 / 3,
            child: Image.asset(
              'assets/images/year_motto_pig_rockers.jpg',
              fit: BoxFit.cover,
            ),
          ),
          const Padding(
            padding: EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Jahresmotto folgt',
                  style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800),
                ),
                SizedBox(height: 10),
                Text(
                  'Hier erhält das aktuelle FLAPAMAMAKU-Jahresmotto seinen eigenen Platz. '
                  'Logo, Motto-Text, Bilder und weitere Informationen können später zentral gepflegt werden.',
                  style: TextStyle(fontSize: 17, height: 1.45),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
