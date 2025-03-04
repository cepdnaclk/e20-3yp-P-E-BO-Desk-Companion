import 'package:flutter/material.dart';
import '../widgets/custom_app_bar.dart';
import '../widgets/custom_drawer.dart';
import '../widgets/custom_nav_bar.dart';

class HomeScreen extends StatefulWidget {
  final String title;
  final int currentNavIndex;
  const HomeScreen({
    Key? key,
    required this.title,
    required this.currentNavIndex,
  }) : super(key: key);

  @override
  _HomeScreenState createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  int _currentNavIndex = 0; // Track the selected navigation index

  // Dummy data for featured items
  final List<Map<String, dynamic>> _featuredItems = [
    {
      'icon': Icons.task,
      'title': 'Tasks',
      'color': Colors.blue,
      'route': '/tasks',
    },
    {
      'icon': Icons.settings,
      'title': 'Setup',
      'color': Colors.green,
      'route': '/setup',
    },
    {
      'icon': Icons.analytics,
      'title': 'Analytics',
      'color': Colors.orange,
      'route': '/analytics',
    },
    {
      'icon': Icons.notifications,
      'title': 'Notifications',
      'color': Colors.purple,
      'route': '/notifications',
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(
        title: 'Home',
        showBackButton: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.notifications, color: Colors.white),
            onPressed: () {
              Navigator.pushNamed(context, '/notifications');
            },
          ),
        ],
      ),
      drawer: const CustomDrawer(),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Welcome message
            Text(
              'Welcome back, User!',
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                fontWeight: FontWeight.bold,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'What would you like to do today?',
              style: Theme.of(
                context,
              ).textTheme.bodyLarge?.copyWith(color: Colors.grey[600]),
            ),
            const SizedBox(height: 24),

            // Featured grid
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
                childAspectRatio: 1.2,
              ),
              itemCount: _featuredItems.length,
              itemBuilder: (context, index) {
                final item = _featuredItems[index];
                return _buildFeatureCard(
                  icon: item['icon'],
                  title: item['title'],
                  color: item['color'],
                  onTap: () {
                    Navigator.pushNamed(context, item['route']);
                  },
                );
              },
            ),
            const SizedBox(height: 24),

            // Recent activity section
            Text(
              'Recent Activity',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            _buildActivityList(),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () {
          // Add a new task or action
          Navigator.pushNamed(context, '/add-task');
        },
        child: const Icon(Icons.add, color: Colors.white),
        backgroundColor: Theme.of(context).colorScheme.primary,
      ),
      bottomNavigationBar: CustomNavBar(
        currentIndex: _currentNavIndex,
        onTap: (index) {
          setState(() {
            _currentNavIndex = index;
          });
          // Handle navigation based on index
          switch (index) {
            case 0:
              Navigator.pushNamed(context, '/home');
              break;
            case 1:
              Navigator.pushNamed(context, '/tasks');
              break;
            case 2:
              Navigator.pushNamed(context, '/setup');
              break;
          }
        },
      ),
    );
  }

  // Build a feature card
  Widget _buildFeatureCard({
    required IconData icon,
    required String title,
    required Color color,
    required VoidCallback onTap,
  }) {
    return Card(
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 40, color: color),
              const SizedBox(height: 8),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // Build a list of recent activities
  Widget _buildActivityList() {
    final List<Map<String, dynamic>> activities = [
      {
        'icon': Icons.task,
        'title': 'Task Completed',
        'subtitle': 'You completed "Setup PEBO Device"',
        'time': '2 hours ago',
      },
      {
        'icon': Icons.notifications,
        'title': 'New Notification',
        'subtitle': 'Your device is ready for setup',
        'time': '5 hours ago',
      },
      {
        'icon': Icons.settings,
        'title': 'Device Connected',
        'subtitle': 'PEBO Device #1234 is now connected',
        'time': '1 day ago',
      },
    ];

    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: activities.length,
      itemBuilder: (context, index) {
        final activity = activities[index];
        return ListTile(
          leading: Icon(activity['icon'], color: Colors.blue),
          title: Text(activity['title']),
          subtitle: Text(activity['subtitle']),
          trailing: Text(
            activity['time'],
            style: const TextStyle(color: Colors.grey),
          ),
        );
      },
    );
  }
}
