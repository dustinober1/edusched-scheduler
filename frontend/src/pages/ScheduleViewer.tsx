import ScheduleCalendar from '../components/ScheduleCalendar';

export default function ScheduleViewer() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Schedule Viewer</h1>
        <p className="mt-2 text-sm text-gray-600">
          View and analyze the generated schedules
        </p>
      </div>

      <ScheduleCalendar
        assignments={[]}
        editable={false}
        view="timeGridWeek"
      />
    </div>
  );
}