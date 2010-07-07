--------------------------------------------------------------------------------
-- Notes:
--
-- Unfortunately MySQL has a longtime annoyance: it does not support
-- milliseconds nor microseconds in the timestamps (even it allocates
-- 8 bytes per a timestamp). Thus, BIGINTs. Slightly inconvenient,
-- since formatting becomes tedious, but it works and is commonly used
-- as a workaround.  9223372036854775807 equals to 2**63-1.
--
-- Using MyISAM storage engine results in 'Got error code 124 from
-- storage engine' errors while updating and querying snapshot tables.
-- Hence, we are currently forced to InnoDB, which is slightly worse
-- performing. Fortunately, as a trade-off we get full ACID semantics.
--
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
-- Flow event and network database table logs
--------------------------------------------------------------------------------

DROP TABLE IF EXISTS FLOW;
CREATE TABLE FLOW (
      ID                     INTEGER NOT NULL AUTO_INCREMENT,

      -- OpenFlow
      CREATED_DT             BIGINT NOT NULL, 
      DELETED_DT             BIGINT NOT NULL DEFAULT 9223372036854775807,
      DP_ID                  BIGINT UNSIGNED NOT NULL,
      PORT_ID                SMALLINT UNSIGNED,

      -- L2
      ETH_VLAN               SMALLINT UNSIGNED,
      ETH_TYPE               SMALLINT UNSIGNED,
      SOURCE_MAC             BIGINT,
      DESTINATION_MAC        BIGINT,

      -- L3
      SOURCE_IP              INTEGER UNSIGNED,
      SOURCE_IP_MASK         INTEGER UNSIGNED,
      DESTINATION_IP         INTEGER UNSIGNED,
      DESTINATION_IP_MASK    INTEGER UNSIGNED,
      PROTOCOL_ID            SMALLINT UNSIGNED,

      -- L4
      SOURCE_PORT            SMALLINT UNSIGNED,
      DESTINATION_PORT       SMALLINT UNSIGNED,

      -- Stats
      DURATION               INTEGER UNSIGNED,
      PACKET_COUNT           BIGINT UNSIGNED,
      BYTE_COUNT             BIGINT UNSIGNED,

      PRIMARY KEY(ID),
      INDEX(CREATED_DT)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS FLOW_STAGING;
CREATE TABLE FLOW_STAGING (
      ID                     INTEGER NOT NULL AUTO_INCREMENT,

      TYPE                   CHAR(1) NOT NULL, -- 'O'pen or 'C'lose
      CREATED_DT             BIGINT NOT NULL,

      DP_ID                  BIGINT UNSIGNED NOT NULL,
      PORT_ID                SMALLINT UNSIGNED,

      -- L2
      ETH_VLAN               SMALLINT UNSIGNED,
      ETH_TYPE               SMALLINT UNSIGNED,
      SOURCE_MAC             BIGINT,
      DESTINATION_MAC        BIGINT,

      -- L3
      SOURCE_IP              INTEGER UNSIGNED,
      SOURCE_IP_MASK         INTEGER UNSIGNED,
      DESTINATION_IP         INTEGER UNSIGNED,
      DESTINATION_IP_MASK    INTEGER UNSIGNED,
      PROTOCOL_ID            SMALLINT UNSIGNED,

      -- L4
      SOURCE_PORT            SMALLINT UNSIGNED,
      DESTINATION_PORT       SMALLINT UNSIGNED,

      -- Stats
      DURATION               INTEGER UNSIGNED,
      PACKET_COUNT           BIGINT UNSIGNED,
      BYTE_COUNT             BIGINT UNSIGNED,

      PRIMARY KEY(ID),
      INDEX(CREATED_DT)
)  ENGINE=InnoDB;

DROP TABLE IF EXISTS FLOW_SETUP;
CREATE TABLE FLOW_SETUP (
      ID                     INTEGER NOT NULL AUTO_INCREMENT,

      -- OpenFlow
      CREATED_DT             BIGINT NOT NULL, 
      DELETED_DT             BIGINT NOT NULL DEFAULT 9223372036854775807,

      DP_ID                  BIGINT UNSIGNED NOT NULL,
      PORT_ID                SMALLINT UNSIGNED NOT NULL,
      REASON                 SMALLINT UNSIGNED NOT NULL,
      BUFFER                 VARBINARY(9000) NOT NULL,
      TOTAL_LEN              INTEGER UNSIGNED NOT NULL,

      PRIMARY KEY(ID),
      INDEX(CREATED_DT)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS FLOW_SETUP_STAGING;
CREATE TABLE FLOW_SETUP_STAGING (
      ID                     INTEGER NOT NULL AUTO_INCREMENT,

      TYPE                   CHAR(1) NOT NULL, -- 'O'pen or 'C'lose
      CREATED_DT             BIGINT NOT NULL,

      DP_ID                  BIGINT UNSIGNED NOT NULL,
      PORT_ID                SMALLINT UNSIGNED NOT NULL,
      REASON                 SMALLINT UNSIGNED NOT NULL,
      BUFFER                 VARBINARY(9000) NOT NULL,
      TOTAL_LEN              INTEGER UNSIGNED NOT NULL,

      PRIMARY KEY(ID),
      INDEX(CREATED_DT)
) ENGINE=InnoDB;


DROP TABLE IF EXISTS LLDP_LINKS;
CREATE TABLE LLDP_LINKS (
      ID                     INTEGER NOT NULL AUTO_INCREMENT,

      -- OpenFlow
      CREATED_DT             BIGINT NOT NULL,
      DELETED_DT             BIGINT NOT NULL DEFAULT 9223372036854775807,

      DP1                    BIGINT UNSIGNED NOT NULL,
      PORT1                  SMALLINT NOT NULL,
      DP2                    BIGINT UNSIGNED NOT NULL,
      PORT2                  SMALLINT NOT NULL,

      PRIMARY KEY(ID),
      INDEX(CREATED_DT)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS LLDP_LINKS_STAGING;
CREATE TABLE LLDP_LINKS_STAGING (
      ID                     INTEGER NOT NULL AUTO_INCREMENT,

      TYPE                   CHAR(1) NOT NULL, -- 'O'pen or 'C'lose
      CREATED_DT             BIGINT NOT NULL,

      DP1                    BIGINT UNSIGNED,
      PORT1                  SMALLINT,
      DP2                    BIGINT UNSIGNED,
      PORT2                  SMALLINT,

      PRIMARY KEY(ID),
      INDEX(CREATED_DT)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS LEARNING;
CREATE TABLE LEARNING (
      ID                     INTEGER NOT NULL AUTO_INCREMENT,

      -- OpenFlow
      CREATED_DT             BIGINT NOT NULL,       
      DELETED_DT             BIGINT NOT NULL DEFAULT 9223372036854775807,

      SWITCH_ID              BIGINT NOT NULL,   
      MAC                    BIGINT NOT NULL,
      PORT_ID                SMALLINT NOT NULL,

      PRIMARY KEY(ID),
      INDEX(CREATED_DT)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS LEARNING_STAGING;
CREATE TABLE LEARNING_STAGING (
      ID                     INTEGER NOT NULL AUTO_INCREMENT,

      TYPE                   CHAR(1) NOT NULL, -- 'O'pen or 'C'lose
      CREATED_DT             BIGINT NOT NULL,

      SWITCH_ID              BIGINT,
      MAC                    BIGINT,
      PORT_ID                SMALLINT,

      PRIMARY KEY(ID),
      INDEX(CREATED_DT)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS PF;
CREATE TABLE PF (
      ID                     INTEGER NOT NULL AUTO_INCREMENT,

      -- OpenFlow
      CREATED_DT             BIGINT NOT NULL,       
      DELETED_DT             BIGINT NOT NULL DEFAULT 9223372036854775807,

      MAC                    BIGINT NOT NULL,
      IP                     INTEGER UNSIGNED NOT NULL,
      P0F_OS                 VARCHAR(1024),
      P0F_DESCR              VARCHAR(1024),
      P0F_WSS_MISS           SMALLINT UNSIGNED,
      P0F_DF_MISS            SMALLINT UNSIGNED,
      P0F_ACC                SMALLINT UNSIGNED,
      PF_OS                  VARCHAR(1024),

      PRIMARY KEY(ID),
      INDEX(CREATED_DT)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS PF_STAGING;
CREATE TABLE PF_STAGING (
      ID                     INTEGER NOT NULL AUTO_INCREMENT,

      TYPE                   CHAR(1) NOT NULL, -- 'O'pen or 'C'lose
      CREATED_DT             BIGINT NOT NULL,

      MAC                    BIGINT,
      IP                     INTEGER UNSIGNED,
      P0F_OS                 VARCHAR(1024),
      P0F_DESCR              VARCHAR(1024),
      P0F_WSS_MISS           SMALLINT UNSIGNED,
      P0F_DF_MISS            SMALLINT UNSIGNED,
      P0F_ACC                SMALLINT UNSIGNED,
      PF_OS                  VARCHAR(1024),

      PRIMARY KEY(ID),
      INDEX(CREATED_DT)
) ENGINE=InnoDB;

--------------------------------------------------------------------------------
-- Snapshot tables
--------------------------------------------------------------------------------

DROP TABLE IF EXISTS FLOW_SNAPSHOT;
DROP TABLE IF EXISTS FLOW_SETUP_SNAPSHOT;
DROP TABLE IF EXISTS LLDP_LINKS_SNAPSHOT;
DROP TABLE IF EXISTS LEARNING_SNAPSHOT;
DROP TABLE IF EXISTS PF_SNAPSHOT;

DROP TABLE IF EXISTS SNAPSHOT;
CREATE TABLE SNAPSHOT (
      ID                     INTEGER AUTO_INCREMENT,
      TABLE_ID               INTEGER NOT NULL,
      CREATED_DT             BIGINT NOT NULL,
      PRIMARY KEY(ID),
      INDEX(CREATED_DT)
) ENGINE=InnoDB;

CREATE TABLE FLOW_SNAPSHOT (
      FLOW_ID                INTEGER NOT NULL,
      SNAPSHOT_ID            INTEGER NOT NULL,
      FOREIGN KEY (SNAPSHOT_ID) REFERENCES SNAPSHOT (ID)
) ENGINE=InnoDB;


CREATE TABLE FLOW_SETUP_SNAPSHOT (
      FLOW_SETUP_ID          INTEGER NOT NULL,
      SNAPSHOT_ID            INTEGER NOT NULL,
      FOREIGN KEY (SNAPSHOT_ID) REFERENCES SNAPSHOT (ID)
) ENGINE=InnoDB;


CREATE TABLE LLDP_LINKS_SNAPSHOT (
      LLDP_LINKS_ID           INTEGER NOT NULL,
      SNAPSHOT_ID            INTEGER NOT NULL,
      FOREIGN KEY (SNAPSHOT_ID) REFERENCES SNAPSHOT (ID)
) ENGINE=InnoDB;

CREATE TABLE LEARNING_SNAPSHOT (
      LEARNING_ID            INTEGER NOT NULL,
      SNAPSHOT_ID            INTEGER NOT NULL,
      FOREIGN KEY (SNAPSHOT_ID) REFERENCES SNAPSHOT (ID)
) ENGINE=InnoDB;

CREATE TABLE PF_SNAPSHOT (
      PF_ID                  INTEGER NOT NULL,
      SNAPSHOT_ID            INTEGER NOT NULL,
      FOREIGN KEY (SNAPSHOT_ID) REFERENCES SNAPSHOT (ID)
) ENGINE=InnoDB;

--------------------------------------------------------------------------------
-- Tables and procedures for loading.
--------------------------------------------------------------------------------

DROP TABLE IF EXISTS LOAD_SOURCE;
CREATE TABLE LOAD_SOURCE (
      ID                     INTEGER AUTO_INCREMENT,
      NAME                   VARCHAR(256) NOT NULL,
      PRIMARY KEY(ID)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS LOAD_TABLE;
CREATE TABLE LOAD_TABLE (
      ID                     INTEGER AUTO_INCREMENT,
      NAME                   VARCHAR(256) NOT NULL,
      PRIMARY KEY(ID)
) ENGINE=InnoDB;

DROP TABLE IF EXISTS LOAD_LOG;
CREATE TABLE LOAD_LOG (
      ID                     INTEGER AUTO_INCREMENT,
      SOURCE_ID              INTEGER NOT NULL REFERENCES LOAD_SOURCE(ID),
      TABLE_ID               INTEGER NOT NULL REFERENCES LOAD_TABLE(ID),
      FILE_NAME              VARCHAR(256) NOT NULL,
      OLDEST_ENTRY_DT        BIGINT NOT NULL,
      LATEST_ENTRY_DT        BIGINT NOT NULL,
      CREATED_DT             TIMESTAMP NOT NULL,
      PRIMARY KEY(ID),
      INDEX(CREATED_DT)
) ENGINE=InnoDB;

DROP PROCEDURE IF EXISTS PRE_PROCESS_FLOW;
DELIMITER //
CREATE PROCEDURE PRE_PROCESS_FLOW ()
BEGIN
        DECLARE DONE INTEGER DEFAULT 0;
        DECLARE V_TYPE CHAR(1);
        DECLARE V_CREATED_DT BIGINT;
        DECLARE V_DP_ID BIGINT UNSIGNED;
        DECLARE V_PORT_ID SMALLINT UNSIGNED;
        DECLARE V_ETH_VLAN SMALLINT UNSIGNED;
        DECLARE V_ETH_TYPE SMALLINT UNSIGNED;
        DECLARE V_SOURCE_MAC BIGINT;
        DECLARE V_DESTINATION_MAC BIGINT;
        DECLARE V_SOURCE_IP INTEGER UNSIGNED;
        DECLARE V_SOURCE_IP_MASK INTEGER UNSIGNED;
        DECLARE V_DESTINATION_IP INTEGER UNSIGNED;
        DECLARE V_DESTINATION_IP_MASK INTEGER UNSIGNED;
        DECLARE V_PROTOCOL_ID SMALLINT UNSIGNED;
        DECLARE V_SOURCE_PORT SMALLINT UNSIGNED;
        DECLARE V_DESTINATION_PORT SMALLINT UNSIGNED;
        DECLARE V_DURATION INTEGER UNSIGNED;
        DECLARE V_PACKET_COUNT BIGINT UNSIGNED;
        DECLARE V_BYTE_COUNT BIGINT UNSIGNED;

        DECLARE CUR1 CURSOR FOR SELECT TYPE, CREATED_DT, DP_ID, PORT_ID, 
                    ETH_VLAN, ETH_TYPE, SOURCE_MAC, DESTINATION_MAC, 
                    SOURCE_IP, SOURCE_IP_MASK,
                    DESTINATION_IP, DESTINATION_IP_MASK,
                    PROTOCOL_ID, SOURCE_PORT, 
                    DESTINATION_PORT, DURATION, PACKET_COUNT, BYTE_COUNT
                    FROM FLOW_STAGING 
                    ORDER BY CREATED_DT, ID;
        DECLARE CONTINUE HANDLER FOR NOT FOUND SET DONE = 1;
        
        OPEN CUR1;
        
        -- Iterate through the new entries to insert a new into
        -- FLOW table or to close an existing one.
        REPEAT
                FETCH CUR1 INTO V_TYPE, V_CREATED_DT, V_DP_ID, V_PORT_ID, 
                    V_ETH_VLAN, V_ETH_TYPE, V_SOURCE_MAC, V_DESTINATION_MAC, 
                    V_SOURCE_IP, V_SOURCE_IP_MASK,
                    V_DESTINATION_IP, V_DESTINATION_IP_MASK, V_PROTOCOL_ID, 
                    V_SOURCE_PORT, V_DESTINATION_PORT, V_DURATION, 
                    V_PACKET_COUNT, V_BYTE_COUNT;
                IF NOT DONE THEN      
                       CASE V_TYPE
                          WHEN 'O' THEN    
                               INSERT INTO FLOW(CREATED_DT, DP_ID, PORT_ID, 
                                   ETH_VLAN, ETH_TYPE, SOURCE_MAC, DESTINATION_MAC, 
                                   SOURCE_IP, SOURCE_IP_MASK,
                                   DESTINATION_IP, DESTINATION_IP_MASK,
                                   PROTOCOL_ID, SOURCE_PORT, 
                                   DESTINATION_PORT, DURATION, PACKET_COUNT, BYTE_COUNT)
                                      VALUES(V_CREATED_DT, V_DP_ID, V_PORT_ID,
                                             V_ETH_VLAN, V_ETH_TYPE, V_SOURCE_MAC, 
                                             V_DESTINATION_MAC,
                                             V_SOURCE_IP, V_SOURCE_IP_MASK
                                             V_DESTINATION_IP, V_DESTINATION_IP_MASK,
                                             V_PROTOCOL_ID, 
                                             V_SOURCE_PORT, V_DESTINATION_PORT,
                                             V_DURATION, V_PACKET_COUNT, V_BYTE_COUNT);
                          WHEN 'C' THEN
                               UPDATE FLOW SET DELETED_DT = V_CREATED_DT, 
                                      DURATION = V_DURATION, 
                                      PACKET_COUNT = V_PACKET_COUNT, 
                                      BYTE_COUNT = V_BYTE_COUNT WHERE 
                                      DELETED_DT = 9223372036854775807 AND
                                      (V_DP_ID IS NULL OR DP_ID = V_DP_ID) AND
                                      (V_PORT_ID IS NULL OR PORT_ID = V_PORT_ID) AND
                                      (V_SOURCE_MAC IS NULL OR SOURCE_MAC = V_SOURCE_MAC) AND
                                      (V_DESTINATION_MAC IS NULL OR DESTINATION_MAC = V_DESTINATION_MAC) AND
                                      (V_SOURCE_IP IS NULL OR SOURCE_IP = V_SOURCE_IP) AND
                                      (V_DESTINATION_IP IS NULL OR DESTINATION_IP = V_DESTINATION_IP) AND
                                      (V_PROTOCOL_ID IS NULL OR PROTOCOL_ID = V_PROTOCOL_ID) AND
                                      (V_SOURCE_PORT IS NULL OR SOURCE_PORT = V_SOURCE_PORT) AND
                                      (V_DESTINATION_PORT IS NULL OR DESTINATION_PORT = V_DESTINATION_PORT);
                          WHEN '*' THEN
                               UPDATE FLOW SET DELETED_DT = V_CREATED_DT WHERE 
                                      DELETED_DT = 9223372036854775807;
                       END CASE;
                END IF;
        UNTIL DONE END REPEAT;

        CLOSE CUR1;
        DELETE FROM FLOW_STAGING;
END;
//
DELIMITER ;

DROP PROCEDURE IF EXISTS CREATE_FLOW_SNAPSHOT;
DELIMITER //
CREATE PROCEDURE CREATE_FLOW_SNAPSHOT (IN NEXT_SNAPSHOT_TS BIGINT) 
BEGIN
        DECLARE PREV_SNAPSHOT_TS BIGINT;
        DECLARE PREV_SNAPSHOT_ID INTEGER;
        DECLARE NEXT_SNAPSHOT_ID INTEGER;
        DECLARE FLOW_TABLE_ID INTEGER;

        SELECT ID INTO FLOW_TABLE_ID FROM LOAD_TABLE WHERE NAME = 'FLOW';
        SELECT MAX(ID) INTO PREV_SNAPSHOT_ID FROM SNAPSHOT WHERE TABLE_ID = FLOW_TABLE_ID;
        SELECT MAX(CREATED_DT) INTO PREV_SNAPSHOT_TS FROM SNAPSHOT WHERE ID = PREV_SNAPSHOT_ID;
        IF NEXT_SNAPSHOT_TS > PREV_SNAPSHOT_TS THEN

           -- Create a new snapshot entry
           INSERT INTO SNAPSHOT(CREATED_DT, TABLE_ID) VALUES(NEXT_SNAPSHOT_TS, FLOW_TABLE_ID);
           SET NEXT_SNAPSHOT_ID = LAST_INSERT_ID();

           -- Read the previous snapshot and the flow entries received
           -- since its creation to create a snapshot.
           INSERT INTO FLOW_SNAPSHOT(FLOW_ID, SNAPSHOT_ID)
           SELECT f.ID AS FLOW_ID, NEXT_SNAPSHOT_ID FROM FLOW_SNAPSHOT s, FLOW f WHERE
                  s.SNAPSHOT_ID = PREV_SNAPSHOT_ID AND
                  s.FLOW_ID = f.ID AND
                  f.DELETED_DT > NEXT_SNAPSHOT_TS
           UNION
           SELECT f.ID AS FLOW_ID, NEXT_SNAPSHOT_ID FROM FLOW f WHERE f.CREATED_DT > PREV_SNAPSHOT_TS AND
                  f.CREATED_DT <= NEXT_SNAPSHOT_TS AND
                  f.DELETED_DT > NEXT_SNAPSHOT_TS;
        END IF; 
END;   
//
DELIMITER ;

DROP PROCEDURE IF EXISTS LOAD_FLOW;
DELIMITER //
CREATE PROCEDURE LOAD_FLOW (IN LOAD_SOURCE_ID INTEGER,
                            IN LOAD_FILE_NAME VARCHAR(256))
BEGIN
       DECLARE NEXT_SNAPSHOT_TS BIGINT;
       DECLARE TABLE_ID INT;
       DECLARE LOAD_OLDEST_ENTRY_TS BIGINT;
       DECLARE LOAD_LATEST_ENTRY_TS BIGINT;

       -- Pre-processing step to combine OPEN and CLOSE entries.
       SELECT MIN(CREATED_DT) INTO LOAD_OLDEST_ENTRY_TS FROM FLOW_STAGING;
       SELECT MAX(CREATED_DT) INTO LOAD_LATEST_ENTRY_TS FROM FLOW_STAGING;

       CALL PRE_PROCESS_FLOW();

       -- Log the loaded file.
       SELECT ID INTO TABLE_ID FROM LOAD_TABLE WHERE NAME = 'FLOW';
       INSERT INTO LOAD_LOG(SOURCE_ID, TABLE_ID, FILE_NAME, OLDEST_ENTRY_DT, LATEST_ENTRY_DT, CREATED_DT) 
           VALUES(LOAD_SOURCE_ID, TABLE_ID, LOAD_FILE_NAME, LOAD_OLDEST_ENTRY_TS, LOAD_LATEST_ENTRY_TS, NOW());       

       -- Determine the next snapshot time by finding the highest
       -- LATEST_ENTRY_DT all sources have loaded.
       SELECT MIN(X.LATEST_ENTRY_DT) INTO NEXT_SNAPSHOT_TS FROM (
            SELECT LATEST_ENTRY_DT FROM LOAD_SOURCE LS, LOAD_LOG LL WHERE 
                   LL.TABLE_ID = TABLE_ID AND
                   LS.ID = LL.SOURCE_ID AND LL.LATEST_ENTRY_DT = 
                         (SELECT MAX(LATEST_ENTRY_DT) FROM LOAD_LOG LL2 WHERE LL2.SOURCE_ID = LL.SOURCE_ID)) X;

       -- Build a snapshot, if necessary.
       CALL CREATE_FLOW_SNAPSHOT(NEXT_SNAPSHOT_TS);
END;   
//
DELIMITER ;

DROP PROCEDURE IF EXISTS PRE_PROCESS_FLOW_SETUP;
DELIMITER //
CREATE PROCEDURE PRE_PROCESS_FLOW_SETUP ()
BEGIN
        DECLARE DONE INTEGER DEFAULT 0;
        DECLARE V_TYPE CHAR(1);
        DECLARE V_CREATED_DT BIGINT;
        DECLARE V_DP_ID BIGINT UNSIGNED;
        DECLARE V_PORT_ID SMALLINT UNSIGNED;
        DECLARE V_REASON SMALLINT UNSIGNED;
        DECLARE V_BUFFER VARBINARY(9000);
        DECLARE V_TOTAL_LEN INTEGER UNSIGNED;

        DECLARE CUR1 CURSOR FOR SELECT TYPE, CREATED_DT, DP_ID, PORT_ID, 
                    REASON, BUFFER, TOTAL_LEN FROM FLOW_SETUP_STAGING 
                    ORDER BY CREATED_DT, ID;
        DECLARE CONTINUE HANDLER FOR NOT FOUND SET DONE = 1;
        
        OPEN CUR1;
        
        -- Iterate through the new entries to insert a new into
        -- FLOW_SETUP table or to close an existing one.
        REPEAT
                FETCH CUR1 INTO V_TYPE, V_CREATED_DT, V_DP_ID, V_PORT_ID, 
                    V_REASON, V_BUFFER, V_TOTAL_LEN;
                IF NOT DONE THEN      
                       CASE V_TYPE
                          WHEN 'O' THEN    
                               INSERT INTO FLOW_SETUP(CREATED_DT, DELETED_DT, DP_ID, PORT_ID, REASON, 
                                                      BUFFER, TOTAL_LEN)
                                      VALUES(V_CREATED_DT, V_CREATED_DT, V_DP_ID, V_PORT_ID, 
                                             V_REASON, V_BUFFER, V_TOTAL_LEN);
                          WHEN '*' THEN
                               UPDATE FLOW SET DELETED_DT = V_CREATED_DT WHERE 
                                      DELETED_DT = 9223372036854775807;
                       END CASE;
                END IF;
        UNTIL DONE END REPEAT;

        CLOSE CUR1;
        DELETE FROM FLOW_SETUP_STAGING;
END;
//
DELIMITER ;

DROP PROCEDURE IF EXISTS LOAD_FLOW_SETUP;
DELIMITER //
CREATE PROCEDURE LOAD_FLOW_SETUP (IN LOAD_SOURCE_ID INTEGER,
                                  IN LOAD_FILE_NAME VARCHAR(256))
BEGIN
       DECLARE NEXT_SNAPSHOT_TS BIGINT;
       DECLARE TABLE_ID INT;
       DECLARE LOAD_OLDEST_ENTRY_TS BIGINT;
       DECLARE LOAD_LATEST_ENTRY_TS BIGINT;

       -- Pre-processing step to combine OPEN and CLOSE entries.
       SELECT MIN(CREATED_DT) INTO LOAD_OLDEST_ENTRY_TS FROM FLOW_SETUP_STAGING;
       SELECT MAX(CREATED_DT) INTO LOAD_LATEST_ENTRY_TS FROM FLOW_SETUP_STAGING;

       CALL PRE_PROCESS_FLOW_SETUP();

       -- Log the loaded file.
       SELECT ID INTO TABLE_ID FROM LOAD_TABLE WHERE NAME = 'FLOW_SETUP';
       INSERT INTO LOAD_LOG(SOURCE_ID, TABLE_ID, FILE_NAME, OLDEST_ENTRY_DT, LATEST_ENTRY_DT, CREATED_DT) 
           VALUES(LOAD_SOURCE_ID, TABLE_ID, LOAD_FILE_NAME, LOAD_OLDEST_ENTRY_TS, LOAD_LATEST_ENTRY_TS, NOW());       

       -- No need to build a snapshot, since all entries are immediately closed.
END;   
//
DELIMITER ;

DROP PROCEDURE IF EXISTS PRE_PROCESS_PF;
DELIMITER //
CREATE PROCEDURE PRE_PROCESS_PF ()
BEGIN
        DECLARE DONE INTEGER DEFAULT 0;
        DECLARE V_TYPE CHAR(1);
        DECLARE V_CREATED_DT BIGINT;
        DECLARE V_MAC BIGINT;
        DECLARE V_IP INTEGER UNSIGNED;
        DECLARE V_P0F_OS VARCHAR(1024);
        DECLARE V_P0F_DESCR VARCHAR(1024);
        DECLARE V_P0F_WSS_MISS SMALLINT UNSIGNED;
        DECLARE V_P0F_DF_MISS SMALLINT UNSIGNED;
        DECLARE V_P0F_ACC SMALLINT UNSIGNED;
        DECLARE V_PF_OS VARCHAR(1024);
        DECLARE CUR1 CURSOR FOR SELECT TYPE, CREATED_DT, MAC, IP, P0F_OS, P0F_DESCR, 
                P0F_WSS_MISS, P0F_DF_MISS, P0F_ACC, PF_OS
                FROM PF_STAGING ORDER BY CREATED_DT, ID;
        DECLARE CONTINUE HANDLER FOR NOT FOUND SET DONE = 1;
        
        OPEN CUR1;
        
        -- Iterate through the new entries to insert a new into
        -- PF table or to close an existing one.
        REPEAT
                FETCH CUR1 INTO V_TYPE, V_CREATED_DT, V_MAC, V_IP, V_P0F_OS,
                      V_P0F_DESCR, V_P0F_WSS_MISS, V_P0F_DF_MISS, V_P0F_ACC,
                      V_PF_OS;
                IF NOT DONE THEN
                       CASE V_TYPE
                          WHEN 'O' THEN    
                               INSERT INTO PF(CREATED_DT, MAC, IP, P0F_OS, P0F_DESCR, 
                                      P0F_WSS_MISS, P0F_DF_MISS, P0F_ACC, PF_OS)
                                      VALUES(V_CREATED_DT, V_MAC, V_IP, V_P0F_OS,
                                      V_P0F_DESCR, V_P0F_WSS_MISS, V_P0F_DF_MISS, V_P0F_ACC,
                                      V_PF_OS);
                          WHEN 'C' THEN
                               UPDATE PF SET DELETED_DT = V_CREATED_DT WHERE 
                                      DELETED_DT = 9223372036854775807 AND
                                      (V_MAC IS NULL OR IP = V_IP) AND
                                      (V_IP IS NULL OR IP = V_IP);
                          WHEN '*' THEN
                               UPDATE PF SET DELETED_DT = V_CREATED_DT WHERE 
                                      DELETED_DT = 9223372036854775807;
                       END CASE;
                END IF;
        UNTIL DONE END REPEAT;

        CLOSE CUR1;
        DELETE FROM PF;
END;
//
DELIMITER ;

DROP PROCEDURE IF EXISTS CREATE_PF_SNAPSHOT;
DELIMITER //
CREATE PROCEDURE CREATE_PF_SNAPSHOT (IN NEXT_SNAPSHOT_TS BIGINT) 
BEGIN
        DECLARE PREV_SNAPSHOT_TS BIGINT;
        DECLARE PREV_SNAPSHOT_ID INTEGER;
        DECLARE NEXT_SNAPSHOT_ID INTEGER;
        DECLARE PF_TABLE_ID INTEGER;

        SELECT ID INTO PF_TABLE_ID FROM LOAD_TABLE WHERE NAME = 'PF';
        SELECT MAX(ID) INTO PREV_SNAPSHOT_ID FROM SNAPSHOT WHERE TABLE_ID = PF_TABLE_ID;
        SELECT MAX(CREATED_DT) INTO PREV_SNAPSHOT_TS FROM SNAPSHOT WHERE ID = PREV_SNAPSHOT_ID;
        IF NEXT_SNAPSHOT_TS > PREV_SNAPSHOT_TS THEN

           -- Create a new snapshot entry
           INSERT INTO SNAPSHOT(CREATED_DT, TABLE_ID) VALUES(NEXT_SNAPSHOT_TS, PF_TABLE_ID);
           SET NEXT_SNAPSHOT_ID = LAST_INSERT_ID();

           -- Read the previous snapshot and the flow entries received
           -- since its creation to create a snapshot.
           INSERT INTO PF_SNAPSHOT(PF_ID, SNAPSHOT_ID)
           SELECT f.ID AS PF_ID, NEXT_SNAPSHOT_ID FROM PF_SNAPSHOT s, PF f WHERE
                  s.SNAPSHOT_ID = PREV_SNAPSHOT_ID AND
                  s.PF_ID = f.ID AND
                  f.DELETED_DT > NEXT_SNAPSHOT_TS
           UNION
           SELECT f.ID AS PF_ID, NEXT_SNAPSHOT_ID FROM PF f WHERE f.CREATED_DT > PREV_SNAPSHOT_TS AND
                  f.CREATED_DT <= NEXT_SNAPSHOT_TS AND
                  f.DELETED_DT > NEXT_SNAPSHOT_TS;
        END IF; 
END;   
//
DELIMITER ;

DROP PROCEDURE IF EXISTS LOAD_PF;
DELIMITER //
CREATE PROCEDURE LOAD_PF (IN LOAD_SOURCE_ID INTEGER,
                          IN LOAD_FILE_NAME VARCHAR(256))
BEGIN
       DECLARE NEXT_SNAPSHOT_TS BIGINT;
       DECLARE TABLE_ID INT;
       DECLARE LOAD_OLDEST_ENTRY_TS BIGINT;
       DECLARE LOAD_LATEST_ENTRY_TS BIGINT;

       -- Pre-processing step to combine OPEN and CLOSE entries.
       SELECT MIN(CREATED_DT) INTO LOAD_OLDEST_ENTRY_TS FROM PF_STAGING;
       SELECT MAX(CREATED_DT) INTO LOAD_LATEST_ENTRY_TS FROM PF_STAGING;

       CALL PRE_PROCESS_PF();

       -- Log the loaded file.
       SELECT ID INTO TABLE_ID FROM LOAD_TABLE WHERE NAME = 'PF';
       INSERT INTO LOAD_LOG(SOURCE_ID, TABLE_ID, FILE_NAME, OLDEST_ENTRY_DT, LATEST_ENTRY_DT, CREATED_DT) 
           VALUES(LOAD_SOURCE_ID, TABLE_ID, LOAD_FILE_NAME, LOAD_OLDEST_ENTRY_TS, LOAD_LATEST_ENTRY_TS, NOW());       

       -- Determine the next snapshot time by finding the highest
       -- LATEST_ENTRY_DT all sources have loaded.
       SELECT MIN(X.LATEST_ENTRY_DT) INTO NEXT_SNAPSHOT_TS FROM (
            SELECT LATEST_ENTRY_DT FROM LOAD_SOURCE LS, LOAD_LOG LL WHERE 
                   LL.TABLE_ID = TABLE_ID AND
                   LS.ID = LL.SOURCE_ID AND LL.LATEST_ENTRY_DT = 
                         (SELECT MAX(LATEST_ENTRY_DT) FROM LOAD_LOG LL2 WHERE LL2.SOURCE_ID = LL.SOURCE_ID)) X;

       -- Build a snapshot, if necessary.
       CALL CREATE_PF_SNAPSHOT(NEXT_SNAPSHOT_TS);
END;   
//
DELIMITER ;

DROP PROCEDURE IF EXISTS PRE_PROCESS_LLDP_LINKS;
DELIMITER //
CREATE PROCEDURE PRE_PROCESS_LLDP_LINKS ()
BEGIN
        DECLARE DONE INTEGER DEFAULT 0;
        DECLARE V_TYPE CHAR(1);
        DECLARE V_CREATED_DT BIGINT;
        DECLARE V_DP1 BIGINT UNSIGNED;
        DECLARE V_PORT1 SMALLINT;
        DECLARE V_DP2 BIGINT UNSIGNED;
        DECLARE V_PORT2 SMALLINT;
        DECLARE CUR1 CURSOR FOR SELECT TYPE, CREATED_DT, DP1, PORT1, DP2, PORT2 
                FROM LLDP_LINKS_STAGING ORDER BY CREATED_DT, ID;
        DECLARE CONTINUE HANDLER FOR NOT FOUND SET DONE = 1;
        
        OPEN CUR1;
        
        -- Iterate through the new entries to insert a new into
        -- LLDP_LINKS table or to close an existing one.
        REPEAT
                FETCH CUR1 INTO V_TYPE, V_CREATED_DT, V_DP1, V_PORT1, V_DP2, V_PORT2;
                IF NOT DONE THEN      
                       CASE V_TYPE
                          WHEN 'O' THEN    
                               INSERT INTO LLDP_LINKS(CREATED_DT, DP1, PORT1, DP2, PORT2) 
                                      VALUES(V_CREATED_DT, V_DP1, V_PORT1, V_DP2, V_PORT2);
                          WHEN 'C' THEN
                               UPDATE LLDP_LINKS SET DELETED_DT = V_CREATED_DT WHERE 
                                      DELETED_DT = 9223372036854775807 AND
                                      (V_DP1 IS NULL OR DP1 = V_DP1) AND
                                      (V_DP2 IS NULL OR DP2 = V_DP2) AND
                                      (V_PORT1 IS NULL OR PORT1 = V_PORT1) AND
                                      (V_PORT2 IS NULL OR PORT2 = V_PORT2);
                          WHEN '*' THEN
                               UPDATE LLDP_LINKS SET DELETED_DT = V_CREATED_DT WHERE 
                                      DELETED_DT = 9223372036854775807;
                       END CASE;
                END IF;
        UNTIL DONE END REPEAT;

        CLOSE CUR1;
        DELETE FROM LLDP_LINKS_STAGING;
END;
//
DELIMITER ;

DROP PROCEDURE IF EXISTS CREATE_LLDP_LINKS_SNAPSHOT;
DELIMITER //
CREATE PROCEDURE CREATE_LLDP_LINKS_SNAPSHOT (IN NEXT_SNAPSHOT_TS BIGINT) 
BEGIN
        DECLARE PREV_SNAPSHOT_TS BIGINT;
        DECLARE PREV_SNAPSHOT_ID INTEGER;
        DECLARE NEXT_SNAPSHOT_ID INTEGER;
        DECLARE LLDP_LINKS_TABLE_ID INTEGER;

        SELECT ID INTO LLDP_LINKS_TABLE_ID FROM LOAD_TABLE WHERE NAME = 'LLDP_LINKS';
        SELECT MAX(ID) INTO PREV_SNAPSHOT_ID FROM SNAPSHOT WHERE TABLE_ID = LLDP_LINKS_TABLE_ID;
        SELECT MAX(CREATED_DT) INTO PREV_SNAPSHOT_TS FROM SNAPSHOT WHERE ID = PREV_SNAPSHOT_ID;
        IF NEXT_SNAPSHOT_TS > PREV_SNAPSHOT_TS THEN

           -- Create a new snapshot entry
           INSERT INTO SNAPSHOT(CREATED_DT, TABLE_ID) VALUES(NEXT_SNAPSHOT_TS, LLDP_LINKS_TABLE_ID);
           SET NEXT_SNAPSHOT_ID = LAST_INSERT_ID();

           -- Read the previous snapshot and the flow entries received
           -- since its creation to create a snapshot.
           INSERT INTO LLDP_LINKS_SNAPSHOT(LLDP_LINKS_ID, SNAPSHOT_ID)
           SELECT f.ID AS LLDP_LINKS_ID, NEXT_SNAPSHOT_ID FROM LLDP_LINKS_SNAPSHOT s, LLDP_LINKS f WHERE 
                  s.SNAPSHOT_ID = PREV_SNAPSHOT_ID AND
                  s.LLDP_LINKS_ID = f.ID AND
                  f.DELETED_DT > NEXT_SNAPSHOT_TS
           UNION
           SELECT f.ID AS LLDP_LINKS_ID, NEXT_SNAPSHOT_ID FROM LLDP_LINKS f WHERE f.CREATED_DT > PREV_SNAPSHOT_TS AND
                  f.CREATED_DT <= NEXT_SNAPSHOT_TS AND
                  f.DELETED_DT > NEXT_SNAPSHOT_TS;
        END IF; 
END;   
//
DELIMITER ;

DROP PROCEDURE IF EXISTS LOAD_LLDP_LINKS;
DELIMITER //
CREATE PROCEDURE LOAD_LLDP_LINKS (IN LOAD_SOURCE_ID INTEGER,       
                                  IN LOAD_FILE_NAME VARCHAR(256))
BEGIN
       DECLARE NEXT_SNAPSHOT_TS BIGINT;
       DECLARE TABLE_ID INT;
       DECLARE LOAD_OLDEST_ENTRY_TS BIGINT;
       DECLARE LOAD_LATEST_ENTRY_TS BIGINT;

       -- Pre-processing step to combine OPEN and CLOSE entries.
       SELECT MIN(CREATED_DT) INTO LOAD_OLDEST_ENTRY_TS FROM LLDP_LINKS_STAGING;
       SELECT MAX(CREATED_DT) INTO LOAD_LATEST_ENTRY_TS FROM LLDP_LINKS_STAGING;

       CALL PRE_PROCESS_LLDP_LINKS();

       -- Log the loaded file.
       SELECT ID INTO TABLE_ID FROM LOAD_TABLE WHERE NAME = 'LLDP_LINKS';
       INSERT INTO LOAD_LOG(SOURCE_ID, TABLE_ID, FILE_NAME, OLDEST_ENTRY_DT, LATEST_ENTRY_DT, CREATED_DT) 
           VALUES(LOAD_SOURCE_ID, TABLE_ID, LOAD_FILE_NAME, LOAD_OLDEST_ENTRY_TS, LOAD_LATEST_ENTRY_TS, NOW());

       -- Determine the next snapshot time by finding the highest
       -- LATEST_ENTRY_DT all sources have loaded.
       SELECT MIN(X.LATEST_ENTRY_DT) INTO NEXT_SNAPSHOT_TS FROM (
            SELECT LATEST_ENTRY_DT FROM LOAD_SOURCE LS, LOAD_LOG LL WHERE 
                   LL.TABLE_ID = TABLE_ID AND
                   LS.ID = LL.SOURCE_ID AND LL.LATEST_ENTRY_DT = 
                         (SELECT MAX(LATEST_ENTRY_DT) FROM LOAD_LOG LL2 WHERE LL2.SOURCE_ID = LL.SOURCE_ID)) X;

       -- Build a snapshot, if necessary.
       CALL CREATE_LLDP_LINKS_SNAPSHOT(NEXT_SNAPSHOT_TS);
END;   
//
DELIMITER ;

DROP PROCEDURE IF EXISTS PRE_PROCESS_LEARNING;
DELIMITER //
CREATE PROCEDURE PRE_PROCESS_LEARNING ()
BEGIN
        DECLARE DONE INTEGER DEFAULT 0;
        DECLARE V_TYPE CHAR(1);
        DECLARE V_CREATED_DT BIGINT;
        DECLARE V_SWITCH_ID BIGINT;
        DECLARE V_MAC BIGINT;
        DECLARE V_PORT_ID SMALLINT;
        DECLARE CUR1 CURSOR FOR SELECT TYPE, CREATED_DT, SWITCH_ID, MAC, PORT_ID
                FROM LEARNING_STAGING ORDER BY CREATED_DT, ID;
        DECLARE CONTINUE HANDLER FOR NOT FOUND SET DONE = 1;
        
        OPEN CUR1;
        
        -- Iterate through the new entries to insert a new into
        -- LEARNING table or to close an existing one.
        REPEAT
                FETCH CUR1 INTO V_TYPE, V_CREATED_DT, V_SWITCH_ID, V_MAC, V_PORT_ID;
                IF NOT DONE THEN
                       CASE V_TYPE
                          WHEN 'O' THEN    
                               INSERT INTO LEARNING(CREATED_DT, SWITCH_ID, MAC, PORT_ID) 
                                      VALUES(V_CREATED_DT, V_SWITCH_ID, V_MAC, V_PORT_ID);
                          WHEN 'C' THEN
                               UPDATE LEARNING SET DELETED_DT = V_CREATED_DT WHERE 
                                      DELETED_DT = 9223372036854775807 AND
                                      (V_SWITCH_ID IS NULL OR SWITCH_ID = V_SWITCH_ID) AND
                                      (V_MAC IS NULL OR MAC = V_MAC) AND
                                      (V_PORT_ID IS NULL OR PORT_ID = V_PORT_ID);
                          WHEN '*' THEN
                               UPDATE LEARNING SET DELETED_DT = V_CREATED_DT WHERE 
                                      DELETED_DT = 9223372036854775807;
                       END CASE;
                END IF;
        UNTIL DONE END REPEAT;

        CLOSE CUR1;
        DELETE FROM LEARNING_STAGING;
END;
//
DELIMITER ;

DROP PROCEDURE IF EXISTS CREATE_LEARNING_SNAPSHOT;
DELIMITER //
CREATE PROCEDURE CREATE_LEARNING_SNAPSHOT (IN NEXT_SNAPSHOT_TS BIGINT) 
BEGIN
        DECLARE PREV_SNAPSHOT_TS BIGINT;
        DECLARE PREV_SNAPSHOT_ID INTEGER;
        DECLARE NEXT_SNAPSHOT_ID INTEGER;
        DECLARE LEARNING_TABLE_ID INTEGER;

        SELECT ID INTO LEARNING_TABLE_ID FROM LOAD_TABLE WHERE NAME = 'LEARNING';
        SELECT MAX(ID) INTO PREV_SNAPSHOT_ID FROM SNAPSHOT WHERE TABLE_ID = LEARNING_TABLE_ID;
        SELECT MAX(CREATED_DT) INTO PREV_SNAPSHOT_TS FROM SNAPSHOT WHERE ID = PREV_SNAPSHOT_ID;
        IF NEXT_SNAPSHOT_TS > PREV_SNAPSHOT_TS THEN

           -- Create a new snapshot entry
           INSERT INTO SNAPSHOT(CREATED_DT, TABLE_ID) VALUES(NEXT_SNAPSHOT_TS, LEARNING_TABLE_ID);
           SET NEXT_SNAPSHOT_ID = LAST_INSERT_ID();

           -- Read the previous snapshot and the flow entries received
           -- since its creation to create a snapshot.
           INSERT INTO LEARNING_SNAPSHOT(LEARNING_ID, SNAPSHOT_ID)
           SELECT f.ID AS LEARNING_ID, NEXT_SNAPSHOT_ID FROM LEARNING_SNAPSHOT s, LEARNING f WHERE
                  s.SNAPSHOT_ID = PREV_SNAPSHOT_ID AND
                  s.LEARNING_ID = f.ID AND
                  f.DELETED_DT > NEXT_SNAPSHOT_TS
           UNION
           SELECT f.ID AS LEARNING_ID, NEXT_SNAPSHOT_ID FROM LEARNING f WHERE f.CREATED_DT > PREV_SNAPSHOT_TS AND
                  f.CREATED_DT <= NEXT_SNAPSHOT_TS AND
                  f.DELETED_DT > NEXT_SNAPSHOT_TS;
        END IF; 
END;   
//
DELIMITER ;

DROP PROCEDURE IF EXISTS LOAD_LEARNING;
DELIMITER //
CREATE PROCEDURE LOAD_LEARNING (IN LOAD_SOURCE_ID INTEGER,       
                                IN LOAD_FILE_NAME VARCHAR(256))
BEGIN
       DECLARE NEXT_SNAPSHOT_TS BIGINT;
       DECLARE TABLE_ID INT;
       DECLARE LOAD_OLDEST_ENTRY_TS BIGINT;
       DECLARE LOAD_LATEST_ENTRY_TS BIGINT;

       -- Pre-processing step to combine OPEN and CLOSE entries.
       SELECT MIN(CREATED_DT) INTO LOAD_OLDEST_ENTRY_TS FROM LEARNING_STAGING;
       SELECT MAX(CREATED_DT) INTO LOAD_LATEST_ENTRY_TS FROM LEARNING_STAGING;

       CALL PRE_PROCESS_LEARNING();

       -- Log the loaded file.
       SELECT ID INTO TABLE_ID FROM LOAD_TABLE WHERE NAME = 'LEARNING';
       INSERT INTO LOAD_LOG(SOURCE_ID, TABLE_ID, FILE_NAME, OLDEST_ENTRY_DT, LATEST_ENTRY_DT, CREATED_DT) 
           VALUES(LOAD_SOURCE_ID, TABLE_ID, LOAD_FILE_NAME, LOAD_OLDEST_ENTRY_TS, LOAD_LATEST_ENTRY_TS, NOW());

       -- Determine the next snapshot time by finding the highest
       -- LATEST_ENTRY_DT all sources have loaded.
       SELECT MIN(X.LATEST_ENTRY_DT) INTO NEXT_SNAPSHOT_TS FROM (
            SELECT LATEST_ENTRY_DT FROM LOAD_SOURCE LS, LOAD_LOG LL WHERE 
                   LL.TABLE_ID = TABLE_ID AND
                   LS.ID = LL.SOURCE_ID AND LL.LATEST_ENTRY_DT = 
                         (SELECT MAX(LATEST_ENTRY_DT) FROM LOAD_LOG LL2 WHERE LL2.SOURCE_ID = LL.SOURCE_ID)) X;

       -- Build a snapshot, if necessary.
       CALL CREATE_LEARNING_SNAPSHOT(NEXT_SNAPSHOT_TS);
END;   
//
DELIMITER ;

--------------------------------------------------------------------------------
-- Initialize the baseline. Note, don't change the order SOURCE,
-- TABLE, SNAPSHOT groups.
--------------------------------------------------------------------------------
INSERT INTO LOAD_SOURCE(NAME) VALUES('default');

INSERT INTO LOAD_TABLE(NAME) VALUES('FLOW');
INSERT INTO LOAD_TABLE(NAME) VALUES('FLOW_SETUP');
INSERT INTO LOAD_TABLE(NAME) VALUES('LLDP_LINKS');
INSERT INTO LOAD_TABLE(NAME) VALUES('LEARNING');
INSERT INTO LOAD_TABLE(NAME) VALUES('PF');

INSERT INTO SNAPSHOT(TABLE_ID, CREATED_DT) SELECT ID AS TABLE_ID, 0 AS CREATED_DT FROM LOAD_TABLE;
