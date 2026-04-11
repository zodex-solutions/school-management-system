import 'package:flutter_test/flutter_test.dart';

import 'package:schoolerdesk/main.dart';

void main() {
  testWidgets('shows splash then login options', (WidgetTester tester) async {
    await tester.pumpWidget(const SchoolerDeskApp());

    expect(find.text('SchoolerDesk'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 3000));

    expect(find.text('Staff Login'), findsOneWidget);
    expect(find.text('Parent Login'), findsOneWidget);
  });
}
