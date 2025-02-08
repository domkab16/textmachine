# textmachine
## A python/flask server to run a SMS gateway

Interfacing with the modem directly using AT commands, this software can send and receive sms messages.

The SIM card is polled every 30 seconds and messages are stored in the database

----------------------

# API Endpoints

### Checking SMS

 - Method - GET
 - Authenticaion - Yes
 - Endpoint - /messages

Returns all received messages in JSON format


### Sending SMS

 - Method - POST
 - Authentication - Yes
 - Endpoint - /send_sms

Body Example
```
{
    "phone_number": "+6427123456",
    "message":"Hellow World"
}
```

Sends the sms message to the specified phone number
