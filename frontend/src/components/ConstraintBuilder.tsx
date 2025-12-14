import React, { useState } from 'react';
import {
  PlusIcon,
  TrashIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

interface Constraint {
  id: string;
  name: string;
  type: 'hard' | 'soft';
  category: string;
  enabled: boolean;
  parameters: Record<string, any>;
}

interface ConstraintBuilderProps {
  constraints: Constraint[];
  onAdd: (constraint: Omit<Constraint, 'id'>) => void;
  onUpdate: (id: string, updates: Partial<Constraint>) => void;
  onDelete: (id: string) => void;
  onToggle: (id: string) => void;
}

const constraintCategories = [
  { value: 'resource', label: 'Resource Allocation' },
  { value: 'temporal', label: 'Time-based' },
  { value: 'capacity', label: 'Capacity' },
  { value: 'personnel', label: 'Personnel' },
  { value: 'location', label: 'Location' },
  { value: 'equipment', label: 'Equipment' },
  { value: 'preference', label: 'Preference' },
];

const constraintTemplates = {
  resource: [
    {
      name: 'Room Availability',
      description: 'Ensure room is available during scheduled time',
      parameters: { roomId: '', timeSlots: [] },
    },
    {
      name: 'No Double Booking',
      description: 'Prevent room from being double booked',
      parameters: {},
    },
    {
      name: 'Room Type Match',
      description: 'Schedule only in specified room types',
      parameters: { allowedTypes: [] },
    },
  ],
  temporal: [
    {
      name: 'No Overlapping Classes',
      description: 'Prevent time conflicts for the same resource',
      parameters: {},
    },
    {
      name: 'Minimum Gap Between Classes',
      description: 'Ensure minimum time between consecutive classes',
      parameters: { gapMinutes: 15 },
    },
    {
      name: 'Preferred Time Slots',
      description: 'Schedule during preferred time ranges',
      parameters: { preferredSlots: [], priority: 'medium' },
    },
  ],
  capacity: [
    {
      name: 'Room Capacity Limit',
      description: 'Ensure room can accommodate enrolled students',
      parameters: { capacityBuffer: 5 },
    },
    {
      name: 'Maximum Class Size',
      description: 'Set maximum enrollment for classes',
      parameters: { maxSize: 30 },
    },
  ],
  personnel: [
    {
      name: 'Instructor Availability',
      description: 'Check instructor availability',
      parameters: { instructorId: '', availableTimes: [] },
    },
    {
      name: 'Maximum Teaching Load',
      description: 'Limit instructor concurrent classes',
      parameters: { maxConcurrent: 2 },
    },
  ],
  location: [
    {
      name: 'Campus Restriction',
      description: 'Limit scheduling to specific campuses',
      parameters: { allowedCampuses: [] },
    },
    {
      name: 'Building Preference',
      description: 'Prefer certain buildings for departments',
      parameters: { buildingPriorities: {} },
    },
  ],
  equipment: [
    {
      name: 'Equipment Availability',
      description: 'Ensure required equipment is available',
      parameters: { equipmentIds: [] },
    },
    {
      name: 'Lab Requirements',
      description: 'Schedule labs with proper equipment',
      parameters: { labType: '', equipment: [] },
    },
  ],
  preference: [
    {
      name: 'Student Preferences',
      description: 'Consider student scheduling preferences',
      parameters: { weight: 0.5 },
    },
    {
      name: 'Minimize Walking Distance',
      description: 'Reduce distance between consecutive classes',
      parameters: { maxDistance: 500 },
    },
  ],
};

export default function ConstraintBuilder({
  constraints,
  onAdd,
  onUpdate,
  onDelete,
  onToggle,
}: ConstraintBuilderProps) {
  const [selectedCategory, setSelectedCategory] = useState('resource');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingConstraint, setEditingConstraint] = useState<Partial<Constraint> | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);

  const handleEdit = (constraint: Constraint) => {
    setEditingId(constraint.id);
    setEditingConstraint(constraint);
    setShowAddForm(true);
  };

  const handleSave = () => {
    if (editingId && editingConstraint) {
      onUpdate(editingId, editingConstraint);
    } else if (editingConstraint) {
      onAdd(editingConstraint as Omit<Constraint, 'id'>);
    }

    // Reset form
    setEditingId(null);
    setEditingConstraint(null);
    setShowAddForm(false);
  };

  const handleCancel = () => {
    setEditingId(null);
    setEditingConstraint(null);
    setShowAddForm(false);
  };

  const getAvailableTemplates = () => {
    return constraintTemplates[selectedCategory as keyof typeof constraintTemplates] || [];
  };

  const renderConstraintParameter = (key: string, value: any, onUpdate: (value: any) => void) => {
    switch (key) {
      case 'gapMinutes':
      case 'capacityBuffer':
      case 'maxSize':
      case 'maxConcurrent':
      case 'maxDistance':
      case 'weight':
        return (
          <input
            type="number"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            value={value || ''}
            onChange={(e) => onUpdate(Number(e.target.value))}
          />
        );
      case 'roomId':
      case 'instructorId':
      case 'labType':
        return (
          <input
            type="text"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            value={value || ''}
            onChange={(e) => onUpdate(e.target.value)}
          />
        );
      case 'allowedTypes':
      case 'allowedCampuses':
      case 'equipmentIds':
      case 'preferredSlots':
      case 'availableTimes':
        return (
          <div className="mt-1">
            {/* Multi-select would go here */}
            <textarea
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              rows={3}
              value={Array.isArray(value) ? value.join('\n') : ''}
              onChange={(e) => onUpdate(e.target.value.split('\n').filter(Boolean))}
              placeholder="Enter one value per line"
            />
          </div>
        );
      case 'priority':
        return (
          <select
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            value={value || ''}
            onChange={(e) => onUpdate(e.target.value)}
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        );
      case 'buildingPriorities':
        return (
          <div className="mt-1">
            <textarea
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
              rows={3}
              value={JSON.stringify(value || {}, null, 2)}
              onChange={(e) => {
                try {
                  onUpdate(JSON.parse(e.target.value));
                } catch {
                  // Invalid JSON
                }
              }}
              placeholder='JSON format: {"building1": 1, "building2": 2}'
            />
          </div>
        );
      default:
        return (
          <input
            type="text"
            className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
            value={value || ''}
            onChange={(e) => onUpdate(e.target.value)}
          />
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Add constraint button */}
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-medium text-gray-900">Constraints</h2>
        <button
          onClick={() => setShowAddForm(true)}
          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          Add Constraint
        </button>
      </div>

      {/* Add/Edit form */}
      {showAddForm && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            {editingId ? 'Edit Constraint' : 'Add New Constraint'}
          </h3>

          {/* Category selection */}
          {!editingId && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Category
              </label>
              <select
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
              >
                {constraintCategories.map(category => (
                  <option key={category.value} value={category.value}>
                    {category.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Template selection */}
          {!editingId && getAvailableTemplates().length > 0 && (
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Template
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {getAvailableTemplates().map((template, index) => (
                  <button
                    key={index}
                    onClick={() => setEditingConstraint({
                      name: template.name,
                      type: 'soft',
                      category: selectedCategory,
                      enabled: true,
                      parameters: { ...template.parameters },
                    })}
                    className="p-3 text-left border border-gray-300 rounded-md hover:border-primary-500 hover:bg-primary-50 transition-colors"
                  >
                    <div className="font-medium text-gray-900">{template.name}</div>
                    <div className="text-sm text-gray-600 mt-1">{template.description}</div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Constraint details */}
          {editingConstraint && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Constraint Name
                </label>
                <input
                  type="text"
                  className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                  value={editingConstraint.name || ''}
                  onChange={(e) => setEditingConstraint({
                    ...editingConstraint,
                    name: e.target.value,
                  })}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Type
                </label>
                <div className="flex space-x-4">
                  <label className="flex items-center">
                    <input
                      type="radio"
                      className="form-radio"
                      value="hard"
                      checked={editingConstraint.type === 'hard'}
                      onChange={(e) => setEditingConstraint({
                        ...editingConstraint,
                        type: e.target.value as 'hard' | 'soft',
                      })}
                    />
                    <span className="ml-2 text-sm text-gray-700">Hard Constraint</span>
                  </label>
                  <label className="flex items-center">
                    <input
                      type="radio"
                      className="form-radio"
                      value="soft"
                      checked={editingConstraint.type === 'soft'}
                      onChange={(e) => setEditingConstraint({
                        ...editingConstraint,
                        type: e.target.value as 'hard' | 'soft',
                      })}
                    />
                    <span className="ml-2 text-sm text-gray-700">Soft Constraint</span>
                  </label>
                </div>
              </div>

              {/* Parameters */}
              {editingConstraint.parameters && Object.entries(editingConstraint.parameters).length > 0 && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Parameters
                  </label>
                  <div className="space-y-3">
                    {Object.entries(editingConstraint.parameters).map(([key, value]) => (
                      <div key={key}>
                        <label className="block text-xs font-medium text-gray-600 capitalize">
                          {key.replace(/([A-Z])/g, ' $1').trim()}
                        </label>
                        {renderConstraintParameter(
                          key,
                          value,
                          (newValue) => setEditingConstraint({
                            ...editingConstraint,
                            parameters: {
                              ...editingConstraint.parameters,
                              [key]: newValue,
                            },
                          })
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Form actions */}
          <div className="flex justify-end space-x-3 mt-6">
            <button
              onClick={handleCancel}
              className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              {editingId ? 'Update' : 'Add'}
            </button>
          </div>
        </div>
      )}

      {/* Constraints list */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="divide-y divide-gray-200">
          {constraints.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-gray-500">No constraints added yet</p>
              <p className="text-sm text-gray-400 mt-1">
                Add constraints to control how the scheduler generates schedules
              </p>
            </div>
          ) : (
            constraints.map((constraint) => (
              <div
                key={constraint.id}
                className={`p-4 hover:bg-gray-50 transition-colors ${
                  !constraint.enabled ? 'opacity-50' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => onToggle(constraint.id)}
                        className={`p-1 rounded-md ${
                          constraint.enabled
                            ? 'text-green-600 hover:bg-green-50'
                            : 'text-gray-400 hover:bg-gray-100'
                        }`}
                      >
                        {constraint.enabled ? (
                          <CheckIcon className="h-5 w-5" />
                        ) : (
                          <XMarkIcon className="h-5 w-5" />
                        )}
                      </button>
                      <div>
                        <h4 className="text-sm font-medium text-gray-900">
                          {constraint.name}
                        </h4>
                        <p className="text-xs text-gray-500">
                          {constraint.category} • {constraint.type}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleEdit(constraint)}
                      className="p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded"
                    >
                      <PencilIcon className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => onDelete(constraint.id)}
                      className="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded"
                    >
                      <TrashIcon className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}