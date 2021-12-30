# Artie Max Python Library

This is a library to control your Artie Max from the Python programming language, based on the Mirobot Python library. It has a simple API which mirrors the basic movements that Artie Max can do. Here's a sample program that runs through the API:

    import artiemax
    
    # Connect to Artie Max, disconnecting automatically once the with statement exits
    #  
    with artiemax.Artiemax() as artie:
      # Put the pen down
      artie.pendown(1)

      # Move forward 100mm
      artie.forward(100)

      # Move back 100mm
      artie.back(100)

      # Turn left 45 degrees
      artie.left(45)

      # Turn right 45 degrees
      artie.right(45)

      # Lift the pen up
      artie.penup()

      # Play a sound
      artie.beep(1)


The API can be used in a chained method style:
    with artiemax.Artiemax() as artie:
      # Put the pen down, set the unit to inches, move forward then back
      artie.pendown(1).inches().forward(4).back(4).penup()

The IP address or hostname can be provided; 192.168.4.1 is the default:

    with artiemax.Artiemax('local.artiemax.io') as artie:
       artie.forward(40)

