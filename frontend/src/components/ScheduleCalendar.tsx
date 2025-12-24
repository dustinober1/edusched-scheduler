import React, { useState, useRef } from 'react';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
  CalendarDaysIcon,
  ViewColumnsIcon,
  SquaresPlusIcon,
} from '@heroicons/react/24/outline';

interface Assignment {
  id: string;
  title: string;
  start: Date;
  end: Date;
  extendedProps: {
    courseCode: string;
    room: string;
    instructor: string;
    department: string;
    capacity: number;
    enrolled: number;
  };
}

interface ScheduleCalendarProps {
  assignments: Assignment[];
  onAssignmentClick?: (assignment: Assignment) => void;
  onDateSelect?: (start: Date, end: Date) => void;
  onAssignmentDrop?: (assignment: Assignment, newDate: Date) => void;
  editable?: boolean;
  view?: 'dayGridMonth' | 'timeGridWeek' | 'timeGridDay';
}

export default function ScheduleCalendar({
  assignments,
  onAssignmentClick,
  onDateSelect,
  onAssignmentDrop,
  editable = false,
  view = 'timeGridWeek',
}: ScheduleCalendarProps) {
  const calendarRef = useRef<FullCalendar>(null);
  const [currentView, setCurrentView] = useState(view);

  const handleEventClick = (info: any) => {
    const assignment = assignments.find(a => a.id === info.event.id);
    if (assignment && onAssignmentClick) {
      onAssignmentClick(assignment);
    }
  };

  const handleDateSelect = (selectInfo: any) => {
    if (onDateSelect) {
      onDateSelect(selectInfo.start, selectInfo.end);
      // Clear selection
      calendarRef.current?.getApi().unselect();
    }
  };

  const handleEventDrop = (dropInfo: any) => {
    const assignment = assignments.find(a => a.id === dropInfo.event.id);
    if (assignment && onAssignmentDrop) {
      onAssignmentDrop(assignment, dropInfo.event.start);
    }
  };

  const handleTodayClick = () => {
    calendarRef.current?.getApi().today();
  };

  const handlePrevClick = () => {
    calendarRef.current?.getApi().prev();
  };

  const handleNextClick = () => {
    calendarRef.current?.getApi().next();
  };

  const handleViewChange = (viewType: string) => {
    setCurrentView(viewType as any);
    calendarRef.current?.getApi().changeView(viewType);
  };

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Calendar Toolbar */}
      <div className="border-b border-gray-200 px-4 py-3 sm:flex sm:items-center sm:justify-between">
        <div className="flex items-center space-x-2">
          <button
            onClick={handlePrevClick}
            className="p-2 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded"
          >
            <ChevronLeftIcon className="h-5 w-5" />
          </button>
          <button
            onClick={handleNextClick}
            className="p-2 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded"
          >
            <ChevronRightIcon className="h-5 w-5" />
          </button>
          <button
            onClick={handleTodayClick}
            className="px-3 py-1 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            Today
          </button>
        </div>

        <div className="mt-3 sm:mt-0 sm:ml-4 flex items-center space-x-2">
          {/* View selector */}
          <div className="flex rounded-md shadow-sm">
            <button
              onClick={() => handleViewChange('dayGridMonth')}
              className={`px-3 py-2 text-sm font-medium rounded-l-md border ${
                currentView === 'dayGridMonth'
                  ? 'bg-primary-100 border-primary-500 text-primary-700'
                  : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              <CalendarDaysIcon className="inline-block h-4 w-4 mr-1" />
              Month
            </button>
            <button
              onClick={() => handleViewChange('timeGridWeek')}
              className={`px-3 py-2 text-sm font-medium border-t border-b -ml-px ${
                currentView === 'timeGridWeek'
                  ? 'bg-primary-100 border-primary-500 text-primary-700'
                  : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              <ViewColumnsIcon className="inline-block h-4 w-4 mr-1" />
              Week
            </button>
            <button
              onClick={() => handleViewChange('timeGridDay')}
              className={`px-3 py-2 text-sm font-medium rounded-r-md border-t border-b -ml-px ${
                currentView === 'timeGridDay'
                  ? 'bg-primary-100 border-primary-500 text-primary-700'
                  : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              <SquaresPlusIcon className="inline-block h-4 w-4 mr-1" />
              Day
            </button>
          </div>

          {/* Action buttons */}
          {editable && (
            <button
              onClick={() => calendarRef.current?.getApi().changeView('timeGridWeek')}
              className="p-2 text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 rounded"
              title="Add new assignment"
            >
              <SquaresPlusIcon className="h-5 w-5" />
            </button>
          )}
        </div>
      </div>

      {/* Calendar */}
      <div className="p-4">
        <FullCalendar
          ref={calendarRef}
          plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
          initialView={currentView}
          headerToolbar={false} // Custom toolbar above
          height="auto"
          editable={editable}
          selectable={!!(editable && onDateSelect)}
          selectMirror={true}
          dayMaxEvents={true}
          weekends={true}
          events={assignments.map(assignment => ({
            id: assignment.id,
            title: `${assignment.extendedProps.courseCode} - ${assignment.title}`,
            start: assignment.start,
            end: assignment.end,
            extendedProps: assignment.extendedProps,
            backgroundColor: assignment.extendedProps.department === 'CS' ? '#3b82f6' : '#10b981',
            textColor: '#ffffff',
            borderColor: assignment.extendedProps.department === 'CS' ? '#1d4ed8' : '#059669',
          }))}
          eventClick={handleEventClick}
          select={handleDateSelect}
          eventDrop={handleEventDrop}
          eventContent={(eventInfo) => {
            return (
              <div className="p-1 text-xs">
                <div className="font-semibold">
                  {eventInfo.event.extendedProps.courseCode}
                </div>
                <div className="truncate">
                  {eventInfo.event.title}
                </div>
                <div className="text-xs opacity-75">
                  {eventInfo.event.extendedProps.room}
                </div>
                {eventInfo.event.extendedProps.enrolled > 0 && (
                  <div className="text-xs opacity-75">
                    {eventInfo.event.extendedProps.enrolled}/{eventInfo.event.extendedProps.capacity}
                  </div>
                )}
              </div>
            );
          }}
        />
      </div>
    </div>
  );
}