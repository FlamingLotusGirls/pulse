package org.flg.hiromi.pulsecontroller;

import android.content.Context;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

/**
 * Created by rwk on 2016-08-18.
 */

public class UDPMessageDBHelper extends SQLiteOpenHelper {
    // If you change the database schema, you must increment the database version.
    public static final int DATABASE_VERSION = 1;
    public static final String DATABASE_NAME = "UDPMessages.db";

    private static final String SQL_CREATE_TABLES =
            "CREATE TABLE " + UDPMessage.TABLE_NAME + " ("
                + UDPMessage.FIELD_ID + " INTEGER PRIMARY KEY,"
                + UDPMessage.FIELD_TYPE + " TEXT NOT NULL,"
                + UDPMessage.FIELD_TAG +  " TEXT UNIQUE,"
                + UDPMessage.FIELD_RECEIVER + " INTEGER NOT NULL,"
                + UDPMessage.FIELD_COMMAND + " INTEGER NOT NULL,"
                + UDPMessage.FIELD_DATA + " INTEGER"
                + ")";

    public UDPMessageDBHelper(Context ctx) {
        super(ctx, DATABASE_NAME, null, DATABASE_VERSION);
    }
    @Override
    public void onCreate(SQLiteDatabase db) {
        db.execSQL(SQL_CREATE_TABLES);
    }

    @Override
    public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {

    }
}
