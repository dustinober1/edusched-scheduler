import React from 'react';
import { 
  Card, 
  CardContent, 
  Typography, 
  List, 
  ListItem, 
  ListItemText,
  Divider 
} from '@mui/material';

export const ScheduleCalendar = ({ assignments }) => {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Schedule Calendar
        </Typography>
        <List>
          {assignments && assignments.length > 0 ? (
            assignments.map((assignment) => (
              <React.Fragment key={assignment.id}>
                <ListItem>
                  <ListItemText
                    primary={`${assignment.requestId} - ${assignment.resources.join(', ')}`}
                    secondary={`${assignment.startTime.toDateString()} ${assignment.startTime.toTimeString()} - ${assignment.endTime.toTimeString()}`}
                  />
                </ListItem>
                <Divider />
              </React.Fragment>
            ))
          ) : (
            <ListItem>
              <ListItemText primary="No assignments scheduled" />
            </ListItem>
          )}
        </List>
      </CardContent>
    </Card>
  );
};