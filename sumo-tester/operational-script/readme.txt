1. Run main function 
    - Load detectors from additional file using load_detectors_from_xml function
    - call parse_cross_sections function to map unique lane detectors across same section to have same name for later use
    - Load few user defined parameters
    - load sumo simulation
    - initialize results list for later use
    - initialize detector data dictionary
    - start sumo simulation steps

    - Ego vehicle stop logic
        check if ego is on E1 edge
