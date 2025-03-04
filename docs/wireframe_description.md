{
  "app_name": "PEBO",
  "wireframes": [
    {
      "screen_name": "Home Screen (Dashboard)",
      "description": "Clean dashboard for quick overview.",
      "elements": [
        {
          "type": "Header",
          "content": "PEBO Status",
          "position": "Top",
          "details": "Shows device connection status and notification count"
        },
        {
          "type": "Section",
          "content": "Active Tasks",
          "details": "Displays a summary of tasks in progress"
        },
        {
          "type": "Section",
          "content": "Upcoming Reminders",
          "details": "Shows a preview of the next few reminders"
        },
        {
          "type": "Section",
          "content": "Saved ChatGPT Responses",
          "details":"Preview of recent ChatGPT saves."
        },
        {
          "type": "FAB",
          "content": "+",
          "action": "Add Task",
          "position":"bottom right"
        },
        {
          "type": "Bottom Navigation Bar",
          "items": [
            { "icon": "Tasks", "label": "Tasks" },
            { "icon": "Reminders", "label": "Reminders" },
            { "icon": "Settings", "label": "Settings" },
            { "icon": "Chat", "label": "Chat History" }
          ]
        }
      ]
    },
    {
      "screen_name": "Setup Screen",
      "description": "Guided setup for initial device configuration.",
      "elements": [
        {
          "type": "Header",
          "content": "Initial Setup",
          "position": "Top"
        },
        {
          "type": "Input",
          "label": "Wi-Fi Network",
          "placeholder": "Enter Wi-Fi SSID"
        },
        {
          "type": "Input",
          "label": "Wi-Fi Password",
          "placeholder": "Enter Wi-Fi Password",
          "inputType": "password"
        },
        {
          "type": "Input",
          "label": "API Key",
          "placeholder": "Enter API Key"
        },
        {
          "type": "Button",
          "content": "Save & Connect",
          "action": "Save credentials and initiate connection"
        },
        {
          "type": "Status Indicator",
          "content": "Setup Status",
          "details": "Shows connection and setup completion"
        }
      ]
    },
    {
      "screen_name": "Task Management Screen",
      "description": "List-based task management.",
      "elements": [
        {
          "type": "Header",
          "content": "Tasks",
          "position": "Top"
        },
        {
          "type": "Filter",
          "options": ["Pending", "Completed", "Overdue", "Priority"],
          "details": "Filter tasks by status or priority"
        },
        {
          "type": "Task List",
          "items": [
            { "title": "Task 1", "status": "Pending", "due": "Tomorrow" },
            { "title": "Task 2", "status": "Completed", "due": "Yesterday" },
            { "title": "Task 3", "status": "Overdue", "due": "Last Week" }
          ],
          "details": "Each item includes edit and delete controls"
        },
        {
          "type": "FAB",
          "content": "+",
          "action": "Add Task",
          "position":"bottom right"
        },
        {
          "type": "Bottom Navigation Bar",
          "items": [
            { "icon": "Tasks", "label": "Tasks" },
            { "icon": "Reminders", "label": "Reminders" },
            { "icon": "Settings", "label": "Settings" },
            { "icon": "Chat", "label": "Chat History" }
          ]
        }
      ]
    },
    {
      "screen_name": "Reminders Screen",
      "description": "Scheduling and managing reminders.",
      "elements": [
        {
          "type": "Header",
          "content": "Reminders",
          "position": "Top"
        },
        {
          "type": "View Switch",
          "options": ["List View", "Calendar View"],
          "details": "Switch between list or calendar view"
        },
        {
          "type": "Reminder List",
          "items": [
            { "description": "Reminder 1", "time": "9:00 AM", "type":"One-Time" },
            { "description": "Reminder 2", "time": "Daily 12:00 PM", "type": "Recurring" }
          ]
        },
        {
          "type": "FAB",
          "content": "+",
          "action": "Add Reminder",
          "position":"bottom right"
        },
        {
          "type": "Bottom Navigation Bar",
          "items": [
            { "icon": "Tasks", "label": "Tasks" },
            { "icon": "Reminders", "label": "Reminders" },
            { "icon": "Settings", "label": "Settings" },
            { "icon": "Chat", "label": "Chat History" }
          ]
        }
      ]
    },
    {
      "screen_name": "Settings Screen",
      "description": "Customization and device settings.",
      "elements": [
        {
          "type": "Header",
          "content": "Settings",
          "position": "Top"
        },
        {
          "type": "Setting Group",
          "title": "Notifications",
          "options": [
            { "label": "Task Notifications", "type": "Toggle" },
            { "label": "Reminder Notifications", "type": "Toggle" }
          ]
        },
        {
          "type": "Setting Group",
          "title": "PEBO Device",
          "options": [
            { "label": "Sensor Sensitivity", "type": "Slider" },
            { "label": "Cloud Sync", "type": "Toggle" }
          ]
        },
        {
          "type": "Setting Group",
          "title":"Appearance",
          "options":[
            {"label": "Theme", "type": "Dropdown", "values":["Light", "Dark"]}
          ]
        },
        {
          "type": "Bottom Navigation Bar",
          "items": [
            { "icon": "Tasks", "label": "Tasks" },
            { "icon": "Reminders", "label": "Reminders" },
            { "icon": "Settings", "label": "Settings" },
            { "icon": "Chat", "label": "Chat History" }
          ]
        }
      ]
    },
    {
      "screen_name": "Chat History Screen",
      "description": "List of saved ChatGPT interactions.",
      "elements": [
        {
          "type": "Header",
          "content": "Chat History",
          "position": "Top"
        },
        {
          "type": "Search Bar",
          "placeholder": "Search Chat History"
        },
        {
          "type": "Chat List",
          "items": [
            { "title": "Chat 1", "preview": "Response preview 1..." },
            { "title": "Chat 2", "preview": "Response preview 2..." }
          ]
        },
         {
          "type": "Bottom Navigation Bar",
          "items": [
            { "icon": "Tasks", "label": "Tasks" },
            { "icon": "Reminders", "label": "Reminders" },
            { "icon": "Settings", "label": "Settings" },
            { "icon": "Chat", "label": "Chat History" }
          ]
        }
      ]
    }
  ]
}